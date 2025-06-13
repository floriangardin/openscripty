"""
This module contains the tools related to scripts for the scripty api.
"""

from typing import List
import traceback
from agents import function_tool, RunContextWrapper
from sqlalchemy.orm import Session
from scripty.schemas import ScriptyContext
from scripty.schemas.script import ScriptCreateNoCode, ScriptUpdate, ScriptUpdateNoCode, ScriptRead, ScriptCreate
from scripty.services.script import ScriptService

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


def create_script(
    wrapper: RunContextWrapper[ScriptyContext], script: ScriptCreateNoCode
) -> str:
    """
    Create a script in the database.
    Args:
        script: The script to create.
    """
    print(f"Create script: {script}")
    session: Session = wrapper.context.session
    script = ScriptService.create_script(session, ScriptCreate.model_validate(script.model_dump()))
    wrapper.context.set_current_script_id(script.id)
    return f"Script {script.name} created"


def update_script(
    wrapper: RunContextWrapper[ScriptyContext], script: ScriptUpdateNoCode
) -> str:
    """
    Update a script in the database.
    Args:
        script: The script to update.
    """
    try:
        session: Session = wrapper.context.session
        script_id = wrapper.context.current_script_id
        if script_id is None:
            raise ValueError("No script id found, create it first")
        script = ScriptService.update_script(session, script_id, ScriptUpdate.model_validate(script.model_dump()))
        return f"Script {script.name} updated"
    except Exception as e:
        traceback.print_exc()
        return f"Error updating script: {e}"

@function_tool
def create_or_update_script(
    wrapper: RunContextWrapper[ScriptyContext], script: ScriptCreateNoCode
) -> str:
    """
    Create a new script or update an existing one.
    Args:
        script: The script to create or update.
    """
    try:
        script_id = wrapper.context.current_script_id
        if script_id is None:
            return create_script(wrapper,script)
        return update_script(wrapper, script)
    except Exception as e:
        traceback.print_exc()
        return f"Error creating or updating script: {e}"

@function_tool
async def list_scripts(wrapper: RunContextWrapper[ScriptyContext]) -> List[ScriptRead]:
    """
    List all scripts available to you.
    """
    raw_list = ScriptService.list_scripts(wrapper.context.session)
    return [ScriptRead.model_validate(script) for script in raw_list]

@function_tool
async def switch_script(wrapper: RunContextWrapper[ScriptyContext], script_name: str) -> str:
    """
    Switch to a different current script.
    Args:
        script_name: The name of the script to switch to.
    """
    script = ScriptService.get_script_by_name(wrapper.context.session, script_name)
    wrapper.context.set_current_script_id(script.id)
    return f"Switched to script {script_name}"