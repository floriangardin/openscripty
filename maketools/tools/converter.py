"""
Utils for converting a tool to an usable tool.
"""

from typing import Any
from pydantic import BaseModel
from agents import FunctionTool, RunContextWrapper
from maketools.models.tool import Tool
from maketools.agents.maketools import MaketoolsContext

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


def tool_to_tool(tool: Tool) -> FunctionTool:
    """
    Convert a tool to a tool.
    """

    # pylint: disable=unused-argument
    async def run_function(ctx: RunContextWrapper[MaketoolsContext], args: str) -> str:
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
        name=tool.name,
        description=tool.description,
        params_json_schema=FunctionArgs.model_json_schema(),
        on_invoke_tool=run_function,
    )
