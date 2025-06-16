import json
import jinja2
import asyncio
import os

PYTHON_EXECUTABLE = "python"
signature_template = jinja2.Template("""
import json
from agents.function_schema import function_schema
{{code}}
def inspect_function(func):
    return {"schema": function_schema(func).params_json_schema, "docstring": func.__doc__}

schema = inspect_function(run)
print('<$output>', json.dumps(schema), '</$output>')
""")

async def execute_code(*args, start_token: str, end_token: str, current_dir: str):
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
    print(out)
    err = stderr.decode() if stderr else ""
    code = result.returncode
    if code != 0:
        raise RuntimeError(f"Error running code: {err}")

    string_output = out.split(start_token)[1].split(end_token)[0]
    outputs_data = json.loads(string_output)
    return outputs_data


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
    input_schema = asyncio.run(execute_code(rendered_code, start_token="<$output>", end_token="</$output>", current_dir=os.path.dirname(function_path)))
    function_name = function_path.split('/')[-1].split('.')[0]
    with open(os.path.join(os.path.dirname(function_path), f'{function_name}.json'), 'w', encoding='utf-8') as f:
        json.dump(input_schema, f, indent=2)
    return input_schema

if __name__ == "__main__":
    inspect_function('test_new_funtion/function_pydantic.py')



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