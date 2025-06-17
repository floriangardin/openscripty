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
from maketools.models.tool import Tool
from maketools.schemas.tester import TestResult
from maketools.services.files import FileService
from maketools.services.tool import ToolService   
import jinja2

CODE_WRAPPER_TEMPLATE = jinja2.Template("""
import json
import sys
from agents.function_schema import function_schema
from pydantic import BaseModel
from typing import Callable, TypeVar, Type, Any, get_type_hints
from functools import wraps
import inspect

T = TypeVar('T', bound=BaseModel)

def convert_to_model(data: Any, model_type: Type[BaseModel]) -> BaseModel:
    '''Helper function to convert data to a Pydantic model.'''
    if isinstance(data, model_type):
        return data
    if isinstance(data, dict):
        # If the data is a nested dict with a key matching the model name (case-insensitive)
        model_name = model_type.__name__.lower()
        for key, value in data.items():
            if key.lower() == model_name and isinstance(value, dict):
                return model_type(**value)
        # If no matching key found, try to use the dict directly
        return model_type(**data)
    return data

def pydantic_auto_convert(func: Callable) -> Callable:
    '''
    Decorator that automatically converts dictionary inputs to Pydantic models based on type hints.
    Expects a single dictionary argument containing all parameters.
    '''
    @wraps(func)
    def wrapper(data: dict, **kwargs):
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        new_kwargs = {}
        
        # Process each parameter
        for param_name, param in sig.parameters.items():
            param_type = type_hints.get(param_name)
            
            if param_type and issubclass(param_type, BaseModel):
                # Handle Pydantic model parameters
                new_kwargs[param_name] = convert_to_model(data, param_type)
            elif param_name in data:
                # Handle regular parameters
                new_kwargs[param_name] = data[param_name]
            elif param.default is not inspect.Parameter.empty:
                # Use default value if available
                new_kwargs[param_name] = param.default
            else:
                # Required parameter not found
                raise ValueError(f"Missing required argument: {param_name}")
        
        return func(**new_kwargs)
    return wrapper

{{code}}
result = pydantic_auto_convert(run)(json.loads(sys.argv[1]))

# Wrap the result in a pydantic model to be able to serialize it to json
from typing import Any
class Wrapper(BaseModel):
    wrapped: Any
print('<$output>', json.dumps(Wrapper(wrapped=result).model_dump()['wrapped']), '</$output>')                                
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
    {% for output_arg in tool.outputs %}
    {% if output_arg.type.value == 'file' %}
    output["{{output_arg.name}}"] = tempfile.NamedTemporaryFile(delete=False).name
    {% endif %}
    {% endfor %}
    return output

def execute_function(event: dict, output: dict) -> dict:
    {{code|indent(4)}}
    return output
                                        
def execute_tool(name: str, inputs: dict) -> dict:
    raise NotImplementedError("execute_tool should be mocked")

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
    async def run_code_with_inputs(tool: Tool, workspace_id: str, inputs: dict) -> Dict[str, Any]:
        """
        Run the code with the given inputs.
        Args:
            tool: The tool to run.
            workspace_id: The id of the workspace.
            inputs: The inputs to pass to the code.
        Returns:
            The tool outputs.
        """
        code = tool.code
        full_code = CODE_WRAPPER_TEMPLATE.render(code=code)

        # Execute the code asynchronously
        result = await CodeExecutorService.execute_code([full_code, json.dumps(inputs)], 
                                                        start_token="<$output>", 
                                                        end_token="</$output>", 
                                                        current_dir=FileService.get_file_directory(workspace_id))
        return result
    
    @staticmethod
    async def run_code(tool: Tool, workspace_id: str) -> dict:
        """
        Run the code.
        Args:
            tool: The tool to run.
            workspace_id: The id of the workspace.
        Returns:
            The tool outputs.
        """
        inputs = {v.name: v.value for v in tool.inputs}
        return await CodeExecutorService.run_code_with_inputs(tool, workspace_id, inputs)
    
    @staticmethod
    async def execute_code(args: list[str], start_token: str="<$output>", end_token: str="</$output>", current_dir: str=None) -> dict:
        """Execute the code asynchronously"""
        result = await asyncio.create_subprocess_exec(
            PYTHON_EXECUTABLE,
            "-c",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=current_dir,
        )
        stdout, stderr = await result.communicate()
        out = stdout.decode() if stdout else ""
        err = stderr.decode() if stderr else ""
        code = result.returncode
        if code != 0:
            raise RuntimeError(f"Error running code: {err}")

        string_output = out.split(start_token)[1].split(end_token)[0]
        outputs_data = json.loads(string_output)
        return outputs_data
    
    @staticmethod
    async def run_test(tool: Tool) -> TestResult:
        """
        Run the test.
        Returns:
            The test result.
        """
        test_code = tool.test_code
        test_code = TEST_WRAPPER_TEMPLATE.render(code=tool.code, test_code=test_code, tool=tool)
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
    async def run_with_tool_name(session: Session, workspace_id: str, tool_name: str, inputs: dict) -> Dict[str, Any]:
        """
        Run the code with the tool name.
        Args:
            session: The database session.
            workspace_id: The id of the workspace.
            tool_name: The name of the tool to run.
            inputs: The inputs to pass to the tool.
        Returns:
            The tool outputs.
        """
        tool = ToolService.get_tool_by_name(session, tool_name)
        return await CodeExecutorService.run_code_with_inputs(tool, workspace_id, inputs)