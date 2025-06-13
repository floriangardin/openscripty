"""
The code executor service.
"""
from typing import Dict, Any
import json
import tempfile
import re
import os
import asyncio

from sqlalchemy.orm import Session
from scripty.models.script import ArgumentType, Script
from scripty.schemas.tester import TestResult
from scripty.services.files import FileService
from scripty.services.script import ScriptService   
import jinja2

CODE_WRAPPER_TEMPLATE = jinja2.Template("""
import logging
import argparse
import json
import sys
import os
import requests

logger = logging.getLogger(__name__)

def execute_script(name: str, inputs: dict) -> dict:
    result = requests.post("{{api_url}}/scripts/run", json={"script_name": name, "inputs": inputs})
    if result.status_code != 200:
        raise ValueError(f"Error executing tool {name}: {result.text}")
    return result.json()


inputs = sys.argv[1]
outputs = sys.argv[2]
# Transform args into a event dictionary like in a lambda function
event = json.loads(inputs)
output = json.loads(outputs)

# Main script code begins here
{{code}}
                                 
# Convert output to json
output = json.dumps(output)
# Print output
print('<$output>')
print(output)
print('</$output>')
# TODO: Save FILE & JSON outputs to files and remove them from the output dictionary
""")

TEST_WRAPPER_TEMPLATE = jinja2.Template("""
import sys
import pytest
from pytest import MonkeyPatch
from unittest.mock import patch
import tempfile
import copy
import json

@pytest.fixture
def mock_output():
    # Reconstruct output dict only for FILE type outputs
    output = {}
    {% for output_arg in script.outputs %}
    {% if output_arg.type.value == 'file' %}
    output["{{output_arg.name}}"] = tempfile.NamedTemporaryFile(delete=False).name
    {% endif %}
    {% endfor %}
    return output

def execute_function(event: dict, output: dict) -> dict:
    {{code|indent(4)}}
    return output
                                        
def execute_script(name: str, inputs: dict) -> dict:
    raise NotImplementedError("execute_script should be mocked")

{{test_code}}
                                        
if __name__ == "__main__":
    exit_code = pytest.main(["-v", __file__])
    sys.exit(exit_code)
""")


PYTHON_EXECUTABLE = "python"


class CodeExecutorService:
    """
    Service to execute code.
    """

    @staticmethod
    async def run_code_with_inputs(script: Script, workspace_id: str, inputs: dict) -> Dict[str, Any]:
        """
        Run the code with the given inputs.
        Args:
            script: The script to run.
            workspace_id: The id of the workspace.
            inputs: The inputs to pass to the code.
        Returns:
            The script outputs.
        """
        inputs_data = script.inputs
        outputs_data = script.outputs
        code = script.code
        outputs = {v.name: v.filepath for v in outputs_data}
        full_code = CODE_WRAPPER_TEMPLATE.render(code=code, api_url=os.getenv("API_URL"))

        errors = []
        for input_data in inputs_data:
            if inputs.get(input_data.name) is None:
                errors.append(f"{input_data.name} value is not set")
                continue
            if input_data.type == ArgumentType.FILE:
                if not os.path.exists(os.path.join(
                    FileService.get_file_directory(workspace_id),
                    inputs.get(input_data.name),
                )):
                    errors.append(f"File {input_data.value} not found, maybe the user didn't upload it yet.")
        
        if len(errors) > 0:
            raise ValueError("Some input validation errors occured : \n" + "\n".join(errors))
            
        # Execute the code asynchronously
        result = await asyncio.create_subprocess_exec(
            PYTHON_EXECUTABLE,
            "-c",
            full_code,
            json.dumps(inputs),
            json.dumps(outputs),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=FileService.get_file_directory(workspace_id),
        )
        stdout, stderr = await result.communicate()
        out = stdout.decode() if stdout else ""
        err = stderr.decode() if stderr else ""
        code = result.returncode
        if code != 0:
            raise RuntimeError(f"Error running code: {err}")

        string_output = out.split("<$output>")[1].split("</$output>")[0]
        outputs_data = json.loads(string_output)
        return outputs_data
    
    @staticmethod
    async def run_code(script: Script, workspace_id: str) -> dict:
        """
        Run the code.
        Args:
            script: The script to run.
            workspace_id: The id of the workspace.
        Returns:
            The script outputs.
        """
        inputs = {v.name: v.value for v in script.inputs}
        return await CodeExecutorService.run_code_with_inputs(script, workspace_id, inputs)
    
    @staticmethod
    async def run_test(script: Script) -> TestResult:
        """
        Run the test.
        Returns:
            The test result.
        """
        test_code = script.test_code
        test_code = TEST_WRAPPER_TEMPLATE.render(code=script.code, test_code=test_code, script=script)
        print('test_code : ', test_code)
        
        # Create a temporary file to execute the test code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(test_code)
            temp_file_path = temp_file.name
        
        try:
            result = await asyncio.create_subprocess_exec(
                PYTHON_EXECUTABLE,
                temp_file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            out = stdout.decode() if stdout else ""
            err = stderr.decode() if stderr else ""
            exit_code = result.returncode
            
            print('out : ', out)
            print('err : ', err)
            print('exit_code : ', exit_code)
            
            # Parse pytest exit codes
            # 0: All tests passed
            # 1: Tests were collected and run but some tests failed
            # 2: Test execution was interrupted by the user
            # 3: Internal error happened while executing tests
            # 4: pytest command line usage error
            # 5: No tests were collected
            
            success = False
            details = ""
            
            if exit_code == 0:
                success = True
                details = "All tests passed"
            elif exit_code == 1:
                success = False
                details = "Some tests failed"
            elif exit_code == 2:
                success = False
                details = "Test execution was interrupted"
            elif exit_code == 3:
                success = False
                details = "Internal pytest error"
            elif exit_code == 4:
                success = False
                details = "pytest command line usage error"
            elif exit_code == 5:
                success = False
                details = "No tests were collected"
            else:
                success = False
                details = f"Unknown exit code: {exit_code}"
            
            # Try to extract more detailed information from output
            if out:
                # Look for pytest summary line
                if "failed" in out.lower() and "passed" in out.lower():
                    # Extract test summary (e.g., "1 failed, 2 passed")
                    summary_match = re.search(r'(\d+\s+\w+(?:,\s*\d+\s+\w+)*)', out)
                    if summary_match:
                        details = summary_match.group(1)
                elif "passed" in out.lower() and exit_code == 0:
                    passed_match = re.search(r'(\d+)\s+passed', out)
                    if passed_match:
                        details = f"{passed_match.group(1)} tests passed"
            
            # Fallback: if exit code says success but output shows failures, override
            if exit_code == 0 and "failed" in out.lower():
                success = False
                failed_match = re.search(r'(\d+)\s+failed', out)
                if failed_match:
                    details = f"{failed_match.group(1)} tests failed"
                else:
                    details = "Tests failed (detected from output)"
            
            return TestResult(
                success=success,    
                details=details,
                exit_code=exit_code,
                stdout=out,
                stderr=err
            )
            
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
    
    @staticmethod
    async def run_with_script_name(session: Session, workspace_id: str, script_name: str, inputs: dict) -> Dict[str, Any]:
        """
        Run the code with the script name.
        Args:
            session: The database session.
            workspace_id: The id of the workspace.
            script_name: The name of the script to run.
            inputs: The inputs to pass to the script.
        Returns:
            The script outputs.
        """
        script = ScriptService.get_script_by_name(session, script_name)
        return await CodeExecutorService.run_code_with_inputs(script, workspace_id, inputs)