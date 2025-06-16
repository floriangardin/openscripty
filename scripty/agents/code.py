"""
The code agent.
"""
from agents import Agent, RunContextWrapper, function_tool, Runner
import jinja2
from jinja2 import Template
from scripty.schemas import ScriptyContext
from scripty.models.script import ScriptORM
from scripty.services.code_executor import CodeExecutorService
from scripty.tools.script import list_scripts
from scripty.agents.tester import test_code_with_ai


# pylint: disable=line-too-long

INSTRUCTIONS = """
You are an experienced engineer and expert in python and pydantic. The user is asking you to implement something. 
You generate python code that solves the prompt in a reusable function  called `run`.

<instructions>
1. The function that will be executed is named `run`
2. You must pass a docstring in the `run` function to describe the function.
3. Each parameters of the `run` function must be typed with standard python types OR pydantic models, if you forget a type hint you will fail.
4. You must pass a return type hint to the `run` function, it should be a standard python type OR a pydantic type
5. If you create custom pydantic models for inputs or outputs, you have to define it first in the script code (before `run` function definition)
6. You don't create a __main__ block in the script code, it will be wrapped by the backend code
7. You don't have access to any external library, you must use only standard python types and pydantic models
8. You will have access to some python libraries (see <available_libraries>)
9. If you need to write files, always write them in the current directory (base filepath, see examples).
10. You can create classes and subfunctions in the code that will be called by the `run` function.
11. As implied by 4. the function input and output parameters must be serializable to json, for example you can't pass a pandas dataframe as a parameter.
12. Always return the paths of the files you created or modified in the function output.
</instructions>

<available_libraries>
- standard python librar
- pandas 
- pydantic
- numpy
</available_libraries>

<output_format>
You always format your response in the following format : 

Thoughts : <your thoughts about how to solve the prompt>
Code : ```python
<the python script code that solve the prompt>
```<end_code>

You never forget to enclose your code between ```python and ```<end_code> tags or you will fail.
</output_format>

<examples>
<example_1_simple>
User Prompt : I want to create a function that adds two numbers together

Your response : 
Thoughts : I need to create a function that adds two numbers together, I must type all the parameters and the return type.
Code : ```python
def run(a: int, b: int) -> int:
    '''
    This function adds two numbers together
    Args:
        a: The first number to add
        b: The second number to add
    Returns:
        The sum of the two numbers
    '''
    return a + b
```<end_code>
</example_1_simple>

<example_2_with_pandas>
User Prompt : I want to create a function that reads a csv file and save the first 5 rows in a new csv file

Your response : 
Thoughts : I need to read a csv file and save the first 5 rows in a new csv file, I must use the pandas library.
Code : ```python
import pandas as pd

def run(file_path: str) -> str:
    '''
    This function reads a csv file and save the first 5 rows in a new csv file
    Args:
        file_path: The path to the csv file to read
    Returns:
        output_file_path: The path to the new csv file
    '''
    df = pd.read_csv(file_path)
    # Write in the current directory
    df.head(5).to_csv('first_5_rows.csv', index=False)
    return 'first_5_rows.csv'
```<end_code>
</example_2_with_pandas>

<example_3_with_pydantic>
User Prompt : I need a function that takes a long,lat point and return the distance to the equator in km

Your response : 
Thoughts : I need to create a function that takes a long,lat point and return the distance to the equator in km, I must use the pydantic library. The distance only depends on the latitude.
Code : ```python
from pydantic import BaseModel
from pydantic import Field
import math

class Point(BaseModel):
    '''
    A point with a longitude and latitude
    '''
    long: float = Field(description="The longitude of the point")
    lat: float = Field(description="The latitude of the point")

def run(point: Point) -> float:
    '''
    This function takes a long,lat point and return the distance to the equator in km
    '''
    R = 6371  # Mean Earth radius in kilometers
    return abs(point.lat) * math.pi / 180 * R
```<end_code>
</example_3_with_pydantic>
</examples>

You are in charge of implementing the complete code, not just give directions, create the full code that solve the prompt otherwise you will fail.
"""

# Create user prompt using Jinja template
# pylint: disable=line-too-long
USER_PROMPT_TEMPLATE = Template(
    """
Here is the script brief : 
Name: {{ script_name }}
Description: {{ script_description }}
Additional instructions : 
{{ input }}

{% if current_code %}
Current code : 
```python
{{ current_code }}
```
{% endif %}
"""
)

TEST = False


SIGNATURE_TEMPLATE = jinja2.Template("""
import json
from agents.function_schema import function_schema
from pydantic import BaseModel, TypeAdapter
import typing
                             
{{code}}
                                     
def inspect_function(func):
    output = typing.get_type_hints(run).get('return')
    output_schema = TypeAdapter(output).json_schema()
    return {"schema": function_schema(func).params_json_schema, "docstring": func.__doc__, "output_schema": output_schema}

schema = inspect_function(run)
print('<$output>', json.dumps(schema), '</$output>')
""")

async def inspect_function(function_code: str) -> dict:
    """
    Inspect a function and save the schema to a file
    Args:
        function_path: The path to the function to inspect
    Returns:
        input_schema: The input schema of the function
    """
    rendered_code = SIGNATURE_TEMPLATE.render(code=function_code)
    output = await CodeExecutorService.execute_code([rendered_code])
    return output

# pylint: disable=redefined-builtin,broad-exception-caught
@function_tool
async def create_code_with_ai(
    ctx: RunContextWrapper[ScriptyContext], input: str
) -> str:
    """
    Create a code for the current script using AI.
    Uses the script saved in the database as a spec to generate the code.
    Args:
        input: The prompt given to the code generator. Use it to pass additional information or errors from previous execution to debug the previous code. Don't confuse code creation and execution : pass the prompt to create a generic function here, and then use the execute_code tool to execute the code with appropriate inputs.
    Returns:
        The code for the script.
    """
    print("Creating code")
    try:

        current_script = ctx.context.current_script
        user_prompt = USER_PROMPT_TEMPLATE.render(
            script_name=current_script.name,
            script_description=current_script.description,
            current_code=current_script.code if current_script.code_generated else None,
            input=input,
        )

        agent = Agent[ScriptyContext](
            name="Script code generator",
            model="gpt-4o",
            tools=[list_scripts],
            instructions=INSTRUCTIONS,
        )
        result = await Runner.run(agent, input=user_prompt, context=ctx.context)
        code = result.final_output
        code = code.split("```python")[1].split("```<end_code>")[0]
        inspect_data = await inspect_function(code)
        input_schema = inspect_data["schema"]
        output_schema = inspect_data["output_schema"]
        docstring = inspect_data["docstring"]

        # Update the code in the database using the session
        session = ctx.context.session
        script_orm = (
            session.query(ScriptORM).filter_by(id=ctx.context.current_script_id).first()
        )
        if script_orm:
            script_orm.code = code
            script_orm.touched = True
            script_orm.inputs = input_schema
            script_orm.outputs = output_schema
            script_orm.docstring = docstring
            session.commit()
            session.refresh(script_orm)
        print("Created code :")
        for line in code.split("\n"):
            print(line)

        # Create tests
        result_message = f"""
        Created code successfully for the script. 
        Arguments schema : {input_schema} 
        Outputs : {output_schema}
        Docstring : {docstring}
        """
        if TEST:
            test_result = await test_code_with_ai(ctx.context)
            print("Test result :", test_result.success)
            if test_result.success:
                test_message = "Tested code successfully."
            else:
                test_message = "Weren't able to create working tests."
                test_message += "\n" + test_result.full_output
            result_message += "\n" + test_message

        return result_message
    except Exception as e:
        print(f"Error creating code: {e}")
        return f"Error creating code: {e}"
