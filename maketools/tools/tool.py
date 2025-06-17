"""
This module contains the tools related to tools for the maketools api.
"""

from typing import List
import traceback
from agents import function_tool, RunContextWrapper
from sqlalchemy.orm import Session
from maketools.schemas import MakeToolsContext
from maketools.schemas.tool import ToolCreateNoCode, ToolUpdate, ToolUpdateNoCode, ToolRead, ToolCreate
from maketools.services.tool import ToolService

# pylint: disable=broad-exception-caught

@function_tool
async def say(message: str) -> str:
    """Write an informative message to the user, do not expect a response from the user.
    Don't ask questions with this tool, use your normal output to do that.
    Usually helpful when you are calling a tool and you want to warn the user about it.

    Args:
        message: The message to say to the user.
    """
    print(f"Say: {message}")
    return "Message sent."


def create_tool(
    wrapper: RunContextWrapper[MakeToolsContext], tool: ToolCreateNoCode
) -> str:
    """
    Create a tool in the database.
    Args:
        tool: The tool to create.
    """
    print(f"Create tool: {tool}")
    session: Session = wrapper.context.session
    tool = ToolService.create_tool(session, ToolCreate.model_validate(tool.model_dump()))
    wrapper.context.set_current_tool_id(tool.id)
    return f"Tool named `{tool.name}` created"


def update_tool(
    wrapper: RunContextWrapper[MakeToolsContext], tool: ToolUpdateNoCode
) -> str:
    """
    Update a tool in the database.
    Args:
        tool: The tool to update.
    """
    try:
        session: Session = wrapper.context.session
        tool_id = wrapper.context.current_tool_id
        if tool_id is None:
            raise ValueError("No tool id found, create it first")
        tool = ToolService.update_tool(session, tool_id, ToolUpdate.model_validate(tool.model_dump()))
        return f"Tool named `{tool.name}` updated"
    except Exception as e:
        traceback.print_exc()
        return f"Error updating tool: {e}"

@function_tool
def create_or_update_tool(
    wrapper: RunContextWrapper[MakeToolsContext], tool: ToolCreateNoCode
) -> str:
    """
    Create a new tool or update an existing one.
    Args:
        tool: The tool to create or update.
    """
    try:
        tool_id = wrapper.context.current_tool_id
        if tool_id is None:
            return create_tool(wrapper,tool)
        return update_tool(wrapper, tool)
    except Exception as e:
        traceback.print_exc()
        return f"Error creating or updating tool: {e}"

@function_tool
async def list_tools(wrapper: RunContextWrapper[MakeToolsContext]) -> List[ToolRead]:
    """
    List all tools available to you.
    """
    raw_list = ToolService.list_tools(wrapper.context.session)
    return [ToolRead.model_validate(tool) for tool in raw_list]

@function_tool
async def switch_tool(wrapper: RunContextWrapper[MakeToolsContext], tool_name: str) -> str:
    """
    Switch to a different current tool, usually used to modify an existing tool.
    Args:
        tool_name: The name of the tool to switch to.
    """
    tool = ToolService.get_tool_by_name(wrapper.context.session, tool_name)
    wrapper.context.set_current_tool_id(tool.id)
    return f"Switched to tool named `{tool_name}`"