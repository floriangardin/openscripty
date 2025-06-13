"""
Utils for converting a script to an usable tool.
"""

from typing import Any
from pydantic import BaseModel
from agents import FunctionTool, RunContextWrapper
from scripty.models.script import Script


class FunctionArgs(BaseModel):
    """
    The arguments for the function.
    """

    username: str
    age: int


def do_some_work(data: str) -> str:
    """
    Do some work.
    """
    return "done" + data


def script_to_tool(script: Script) -> FunctionTool:
    """
    Convert a script to a tool.
    """

    # pylint: disable=unused-argument
    async def run_function(ctx: RunContextWrapper[ScriptyContext], args: str) -> str:
        """
        Run the function.
        Args:
            ctx: The context.
            args: The arguments.
        """
        session = ctx.context.session
        parsed = FunctionArgs.model_validate_json(args)
        return do_some_work(data=f"{parsed.username} is {parsed.age} years old")

    return FunctionTool(
        name=script.name,
        description=script.description,
        params_json_schema=FunctionArgs.model_json_schema(),
        on_invoke_tool=run_function,
    )
