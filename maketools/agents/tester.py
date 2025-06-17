"""
The code agent.
"""
import traceback
from typing import Literal
from pydantic import BaseModel
from agents import Agent, RunContextWrapper, function_tool, Runner
from jinja2 import Template
from maketools.schemas import MakeToolsContext
from maketools.models.tool import Tool, ToolORM
from maketools.services.code_executor import CodeExecutorService
from maketools.schemas.tester import TestResult

INSTRUCTIONS = Template("""
You are an expert in testing python code with the pytest framework.
You will be given a function named `execute_function` that takes a dictionary of inputs and a dictionary of outputs.
This is the real signature of the function : 
```python
def execute_function(event: dict, output: dict) -> dict:
    ...
```
It will always return a dictionary with the outputs of the function.
Your job is to write a working test file for the function.
             
<packages_available>
You have access to the following packages : 
- All standard library
- pytest
- pandas
</packages_available>

<output_format>
You will format your answer as the following:

Thoughts: <your thoughts about the tests to write>
Code:
```python
<code>
```<end_code>
</output_format>

<instructions>
1. End your code with the <end_code> tag otherwise you won't succeed.
2. For inputs that are files you need to create them first, ALWAYS use tempfile.NamedTemporaryFile as filepaths, NEVER write a file to the local directory. Use a fixture to create and delete them.
3. You can only write to the files contained in the `output` variable, DON'T TRY TO WRITE ANYWHERE ELSE.
4. The `execute_function` is already imported for you, you don't need to import it in your test code. 
5. You don't have access to any relative packages.
6. If there is some calls to the `execute_tool` function in the function code, you HAVE TO mock the results of all calls to the `execute_tool` function. We don't want to test these behaviours, they are already tested. Just create a function that will return the expected output for the `execute_tool` function called with these arguments.
7. You have access to a fixture called `mock_output` always use it as a fixture of your test functions to get and pass the output dictionary to the `execute_function` function. It will handle the temporary filepaths creation for you. 
8. Only when there is calls to èxecute_tool`: When patching `execute_tool`, always use @patch(f'{__name__}.execute_tool', side_effect=mock_execute_tool) decorator.
</instructions>
                        
<examples>
<example_1_simple_without_execute_tool>
Name: Simple Addition
Description: Add two numbers together and save the result to a file.
Inputs: 
- "number_1" (Type=float) : The first number to add
- "number_2" (Type=float) : The second number to add
Outputs: 
- "sum" (Type=float) : The sum of the two numbers
Code to test : 
```python
def execute_function(event: dict, output: dict) -> dict:
    # Extract input numbers
    num1 = float(event["number_1"])
    num2 = float(event["number_2"])
    
    # Calculate the sum
    result = num1 + num2
    
    # Set the output
    output["sum"] = result
    return output
```
Assistant response : 
Thoughts: This is a simple function that adds two numbers and writes the result to a file. Since there are no calls to `execute_tool`, I don't need to mock anything. I just need to test that the addition is correct.
Code:
```python
import pytest

def test_simple_addition(mock_output):
    inputs = {
        "number_1": 5.0,
        "number_2": 3.0
    }
    result = execute_function(inputs, mock_output)
    
    # Test that the sum is correct
    assert result["sum"] == 8.0
```<end_code>
</example_1_simple_without_execute_tool>

<example_2_with_execute_tool>
Name: String Concatenation
Description: Concatenate three strings together, output the string and save it in a file.
Inputs: 
- "string_1" (Type=string) : The first string to concatenate
- "string_2" (Type=string) : The second string to concatenate
- "string_3" (Type=string) : The third string to concatenate
Outputs: 
- "concatenated_string" (Type=string) : The concatenated string
- "concatenated_string_filepath" (Type=file) : The concatenated string filepath
Code to test : 
```python
def execute_function(event: dict, output: dict) -> dict:
    # Extract input strings
    string1 = event["string1"]
    string2 = event["string2"]
    string3 = event["string3"]

    # Use the String Concatenation tool to concatenate the first two strings
    result1 = execute_tool("String Concatenation", {
        "string_1": string1,
        "string_2": string2
    })

    # Use the String Concatenation tool to concatenate the result with the third string
    final_result = execute_tool("String Concatenation", {
        "string_1": result1["concatenated_string"],
        "string_2": string3
    })

    # Assign the final concatenated string to the output
    output["concatenated_string"] = final_result["concatenated_string"]
    with open(output["concatenated_string_filepath"], "w") as f:
        f.write(final_result["concatenated_string"])
    return output
```
Assistant response : 
Thoughts: I need to test the concatenation of the three strings. There are calls to the `execute_tool` function, I need to mock them.
The function output both the direct string and a filepath to a file. I need to test both, maybe their equality. 
Code:
```python
import pytest
from unittest.mock import patch

def mock_execute_tool(tool_name, inputs):
    # Mock the String Concatenation tool behavior
    if tool_name == "String Concatenation":
        string1 = inputs.get("string_1", "")
        string2 = inputs.get("string_2", "")
        return {"concatenated_string": string1 + string2}
    return {}

# FIXME : THE MODULE IS NOT CALLED test_cli
@patch(f'{__name__}.execute_tool', side_effect=mock_execute_tool)
def test_concatenation(mock_tool, mock_output):
    inputs = {
        "string1": "Hello ",
        "string2": "World ",
        "string3": "Again"
    }
    result = execute_function(inputs, mock_output)
    assert result["concatenated_string"] == "Hello World Again"
    assert result["concatenated_string_filepath"] == mock_output["concatenated_string_filepath"]
    
    # Verify that execute_tool was called twice with the expected arguments
    assert mock_tool.call_count == 2
    mock_tool.assert_any_call("String Concatenation", {"string_1": "Hello ", "string_2": "World "})
    mock_tool.assert_any_call("String Concatenation", {"string_1": "Hello World ", "string_2": "Again"})

</example_2_with_execute_tool>
</examples>
""")

# Create user prompt using Jinja template
# pylint: disable=line-too-long
USER_PROMPT_TEMPLATE = Template(
    """
Here is the `execute_function`function specification : 
Name: {{ tool_name }}
Description: {{ tool_description }}
Inputs: 
{% for input in tool_inputs %}
- "{{ input.name }}" (Type={{ input.type.value }}) {% if input.type.value == "file" %} (filepath) {% endif %} : {{ input.description }}
{% endfor %}
Outputs: 
{% for output in tool_outputs %}
- "{{ output.name }}" (Type={{ output.type.value }}) {% if output.type.value == "file" %} (filepath) {% endif %} : {{ output.description }}
{% endfor %}

{% if input %}
Additional instructions : 
{{ input }}

{% if current_test_code %}
Current test code : 
```python
{{ current_test_code }}
```
{% endif %}

{% endif %}

Code to test : 
```python
def execute_function(event: dict, output: dict) -> dict:
    {{ code }}
```


"""
)

TEST_CODE_WITH_AI_NAME = "Tool test generator"

# pylint: disable=redefined-builtin,broad-exception-caught
async def test_code_with_ai(
    ctx: MakeToolsContext
) -> TestResult:
    """
    Create a test for the current tool using AI.
    Returns:
        The test for the tool.
    """
    print("Creating code")
    max_iteration = 2
    input = None
    code_result = None
    for _ in range(max_iteration):
        try:
            current_tool = ctx.current_tool
            user_prompt = USER_PROMPT_TEMPLATE.render(
                tool_name=current_tool.name,
                tool_description=current_tool.description,
                tool_inputs=current_tool.inputs,
                tool_outputs=current_tool.outputs,
                current_code=current_tool.code,
                input=input,
            )

            agent = Agent[MakeToolsContext](
                name=TEST_CODE_WITH_AI_NAME,
                model="gpt-4o",
                tools=[],
                instructions=INSTRUCTIONS.render(),
            )

            print('User prompt : ', user_prompt)
            result = await Runner.run(agent, input=user_prompt, context=ctx)
            test_code = result.final_output
            test_code = test_code.split("```python")[1].split("```<end_code>")[0]

            # Update the code in the database using the session
            session = ctx.session
            tool_orm = (
                session.query(ToolORM).filter_by(id=ctx.current_tool_id).first()
            )
            if tool_orm:
                tool_orm.test_code = test_code
                session.commit()
                session.refresh(tool_orm)
            
            code_result = await CodeExecutorService.run_test(Tool.model_validate(tool_orm))
            print('Code result : ', code_result.full_output)
            if code_result.success:
                return code_result
            else:
                input = "The tests failed, please check the test code and fix the errors. Here is the full output of the test : " + code_result.full_output
                continue
        except Exception as e:
            ctx.session.rollback()
            print(f"Error creating code: {e}")
            raise RuntimeError(f"Error testing code: {e}") from e
        
    return code_result
