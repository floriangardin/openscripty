import json
import jinja2
import asyncio
import os
from scripty.services.code_executor import CodeExecutorService

PYTHON_EXECUTABLE = "python"
signature_template = jinja2.Template("""
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




def inspect_function(function_path: str) -> dict:
    """
    Inspect a function and save the schema to a file
    Args:
        function_path: The path to the function to inspect
    Returns:
        input_schema: The input schema of the function
    """
    with open(function_path, 'r', encoding='utf-8') as f:
        function_code = f.read()
    rendered_code = signature_template.render(code=function_code)
    output = asyncio.run(CodeExecutorService.execute_code([rendered_code], start_token="<$output>", end_token="</$output>", current_dir=os.path.dirname(function_path)))
    return output

if __name__ == "__main__":
    FUNCTION_PATH = 'test_new_function/function_pydantic.py'
    result = inspect_function(FUNCTION_PATH)
    function_name = FUNCTION_PATH.split('/')[-1].split('.')[0]
    with open(os.path.join(os.path.dirname(FUNCTION_PATH), f'{function_name}.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)



"""
Let the AI generate the script code : 
- You should wrap your main code in a function named `run`
- Each parameters of the `run` function must be typed with standard python types OR pydantic models
- You must pass a return type hint to the `run` function, it should be a standard python type OR a pydantic model
- For each pydantic model you use you have to define it first in the script code (before `run` function definition)
"""

"""
In backend side : when code generated :
- We evaluate the code with get_type_hints to get the type hints of the function
- We create an openapi schema from the type hints (using pydantic-openapi-helper)
"""