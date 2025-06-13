"""
The code agent.
"""
from agents import Agent, RunContextWrapper, function_tool, Runner
from jinja2 import Template
from scripty.schemas import ScriptyContext
from scripty.models.script import ScriptORM
from scripty.tools.script import list_scripts
from scripty.agents.tester import test_code_with_ai


# pylint: disable=line-too-long
CALLING_SCRIPTS = """You also have access to a special function in your code that allows you to call other scripts as a function :
```python
def execute_script(name: str, inputs: dict) -> dict:
```
This function takes the name of the script to call and the inputs to pass to the script.
It returns the output dictionary of the script or raises an error if the script fails.

Here is an example of a script description : 
```json
{
    "name": "String Concatenation",
    "description": "This script takes two strings as inputs and outputs their concatenation.",
    "inputs": [
        {
            "name": "string_1",
            "type": "string",
            "description": "The first string to concatenate.",
            "value": "Hello, "
        },
        {
            "name": "string_2",
            "type": "string",
            "description": "The second string to concatenate.",
            "value": "World!"
        }
    ],
    "outputs": [
        {
            "name": "concatenated_string",
            "type": "string",
            "description": "The result of concatenating the two input strings.",
            "filepath": ""
        },
        {
            "name": "concatenated_string_filepath",
            "type": "file",
            "description": "The result of concatenating the two input strings, saved as a text file.",
            "filepath": "concatenated_string.txt"
        }
    ]
}
```
You can call this script by using the following code : 
```python
result = execute_script("String Concatenation", {
    "string_1": "Hello, ",
    "string_2": "World!"
})
```
It will output the following : 
```json
{
    "concatenated_string": "Hello, World!",
    "concatenated_string_filepath": "concatenated_string.txt"
}
```
You can then reuse the result of the script in your code. For example : 
```python
with open(result["concatenated_string_filepath"], "w") as f:
    result = f.read()
```

Be sure to call the `list_scripts` tool to get the list of scripts available to you before creating your code.
Always reuse existing scripts if possible. Write appropriate adapters if needed.
"""

INSTRUCTIONS = Template("""You are a Python developer expert tasked with creating a script solving a problem given by the user.
You have access to the following libraries:
- all Python standard libraries
- requests
- pandas

To use one of the libraries, just import it as you need.

You already have access to two global variables in your script :
- `event` : A dictionary containing the inputs given by the user. It contains the object except for file inputs where it will be a filepath that you can read using appropriate library.
- `output` : A dictionary containing the outputs of the script. You are responsible of assigning the values to the output dictionary except for file outputs where it will be a filepath to write the file to.

- For FILE inputs, event["input_name"] will be a filepath that you can read using appropriate library.
- For everything except FILE inputs, event["input_name"] will be the object itself.
- For FILE outputs, output["output_name"] will be a filepath to write the file to.
- For everything except FILE outputs, just assign the variable value to the output dictionary available as the variable "output" (eg: output["output_name"] = "value")
- You are allowed to implement helper functions and classes but the main logic must be in the main scope (not in a function)
- Do not use "if __name__ == "__main__"" block, just write the code directly in the main scope (not tabbed), think that your code will be wrapped after you provide it to the user.
- You must output a single file script, not a multi-file script, the code must be self-contained.

<output_format>
You will format your answer as the following:

Thoughts: <your thoughts about the code generation>
Code:
```python
<code>
```<end_code>
</output_format>

<instructions>
1. End your code with the <end_code> tag otherwise you won't succeed.
2. All the variables given by the user (inputs) will be available as a variable called "event" in the code.
3. Don't override the provided `event` variable.
5. As mentionned above : all file outputs are filepaths. Here are some examples of writing files : 
6. You don't have access to any other file than the ones provided in the `event` variable. 
7. You can only write to the files contained in the `output` variable, DON'T TRY TO WRITE ANYWHERE ELSE.
8. You can call other scripts using the `execute_script` function (see below).

```python
# Any text example
with open(output["output_name"], "w") as f:
    f.write("Hello, world!")
# csv example 
df.to_csv(output["output_name"], index=False)
# Upload the Parquet data using the filepath
df.to_parquet(output["output_name"], engine='pyarrow')
```
5. For all other values that are not files, just assign the value to the output variable (eg for text: output["output_name"] = "value")

</instructions>

<examples>
<example1>
User : Here is my brief : 
Name : Concatenate two text files
Description : Concatenate the two text files and save the result in the output file
Inputs : 
- "Text 1" (Type=file) : First text file
- "Text 2" (Type=file) : Second text file
- has_header (Type=bool) : Whether the second csv files has a header
Outputs : 
- "Concatenated CSV" (Type=file) : Concatenated CSV file
- "Error" (Type=bool) : Whether the code has an error

Your answer : 
Thoughts: I need to concatenate the two csv files and save the result in the output file
Code:
```python

text1 = open(event["Text 1"], "r").read()
text2 = open(event["Text 2"], "r").read()
if event["has_header"]:
    text = text1 + text2
else:
    text = text1 + text2
with open(output["Concatenated CSV"], "w") as f:
    f.write(text)
output["Error"] = False
```<end_code>
</example1>

<example2>
Here is the script brief : 
Name : Merge CSV files
Description : Merge the two csv files on the "id" column and save the result in the output file
Inputs : 
- "Csv 1" (Type=file) : First CSV file
- "Csv 2" (Type=file) : Second CSV file
- has_header (Type=bool) : Whether the second csv files has a header
Outputs : 
- "Merged CSV" (Type=file) : Merged CSV file

Your answer : 
Thoughts: I need to merge the two csv files on the "id" column and save the result in the output file
Code:
```python
df1 = pd.read_csv(event["Csv 1"])
df2 = pd.read_csv(event["Csv 2"])
df_merged = pd.merge(df1, df2, on="id", how="left")
requests.put(output["Merged CSV"], data=df_merged.to_csv(index=False))
```<end_code>
</example2>
</examples>

<calling_scripts>
{{ calling_scripts }}
</calling_scripts>
""")

# Create user prompt using Jinja template
# pylint: disable=line-too-long
USER_PROMPT_TEMPLATE = Template(
    """
Here is the script brief : 
Name: {{ script_name }}
Description: {{ script_description }}
Inputs: 
{% for input in script_inputs %}
- "{{ input.name }}" (Type={{ input.type.value }}) {% if input.type.value == "file" %} (filepath) {% endif %} : {{ input.description }}
{% endfor %}
Outputs: 
{% for output in script_outputs %}
- "{{ output.name }}" (Type={{ output.type.value }}) {% if output.type.value == "file" %} (filepath) {% endif %} : {{ output.description }}
{% endfor %}

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
# pylint: disable=redefined-builtin,broad-exception-caught
@function_tool
async def create_code_with_ai(
    ctx: RunContextWrapper[ScriptyContext], input: str
) -> str:
    """
    Create a code for the current script using AI.
    Uses the script saved in the database as a spec to generate the code.
    Args:
        input: The prompt given to the code generator. Use it to pass additional information or errors from previous execution to debug the previous code.
    Returns:
        The code for the script.
    """
    print("Creating code")
    try:

        current_script = ctx.context.current_script
        user_prompt = USER_PROMPT_TEMPLATE.render(
            script_name=current_script.name,
            script_description=current_script.description,
            script_inputs=current_script.inputs,
            script_outputs=current_script.outputs,
            current_code=current_script.code if current_script.code_generated else None,
            input=input,
        )

        agent = Agent[ScriptyContext](
            name="Script code generator",
            model="gpt-4o",
            tools=[list_scripts],
            instructions=INSTRUCTIONS.render(calling_scripts=CALLING_SCRIPTS),
        )
        result = await Runner.run(agent, input=user_prompt, context=ctx.context)
        code = result.final_output
        code = code.split("```python")[1].split("```<end_code>")[0]

        # Update the code in the database using the session
        session = ctx.context.session
        script_orm = (
            session.query(ScriptORM).filter_by(id=ctx.context.current_script_id).first()
        )
        if script_orm:
            script_orm.code = code
            script_orm.touched = True
            session.commit()
            session.refresh(script_orm)
        print("Created code :")
        for line in code.split("\n"):
            print(line)

        # Create tests
        test_message = "Created code successfully for the script"
        if TEST:
            test_result = await test_code_with_ai(ctx.context)
            print("Test result :", test_result.success)
            if test_result.success:
                test_message = "Created and Tested code successfully for the script"
            else:
                test_message = "Created code successfully but weren't able to create working tests for the script"
                test_message += "\n" + test_result.full_output

        return test_message
    except Exception as e:
        print(f"Error creating code: {e}")
        return f"Error creating code: {e}"
