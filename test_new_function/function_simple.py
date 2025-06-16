

def run(a: int, b: int) -> int:
    """
    This function adds two numbers together
    Args:
        a: The first number to add
        b: The second number to add
    Returns:
        The sum of the two numbers
    """
    return a + b



if __name__ == "__main__":
    from agents.function_schema import function_schema
    schema = function_schema(run)
    print(schema.params_json_schema)
    print(run.__doc__)
    from pdb import set_trace
    set_trace()
"""
Let the AI generate the script code : 
- The function that will be executed is named `run`
- Each parameters of the `run` function must be typed with standard python types OR pydantic models
- You must pass a return type hint to the `run` function, it should be a standard python type OR a pydantic model
- For each pydantic model you use you have to define it first in the script code (before `run` function definition)
- You must pass a docstring in the `run` function to describe the function.
"""

"""
In backend side : when code generated :
- We evaluate the code with get_type_hints to get the type hints of the function
- We create an openapi schema from the type hints (using pydantic-openapi-helper)
"""