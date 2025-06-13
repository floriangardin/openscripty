"""
This module contains the schemas for the scripty api.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from scripty.models.script import ScriptInput, ScriptOutput


class ScriptCreateNoCode(BaseModel):
    """
    Create a script in the database.
    """
    name: str = Field(..., description="The name of the script, named like a python function (snake case)")
    description: str = Field(
        ..., description="Full documentation of the script, what it should be doing"
    )
    inputs: List[ScriptInput] = Field(..., description="The inputs of the script")
    outputs: List[ScriptOutput] = Field(..., description="The outputs of the script")

class ScriptCreate(ScriptCreateNoCode):
    """
    Create a script in the database.
    """
    code: Optional[str] = Field(None, description="The code of the script")

class ScriptUpdateNoCode(ScriptCreateNoCode):
    """
    Update a script in the database.
    """

class ScriptUpdate(ScriptUpdateNoCode):
    """
    Update a script in the database.
    """
    code: Optional[str] = Field(None, description="The code of the script")


class ScriptRead(BaseModel):
    """
    Read a script from the database.
    """
    model_config = ConfigDict(from_attributes=True)
    name: str = Field(..., description="The name of the script")
    description: str = Field(
        ..., description="Full documentation of the script, what it should be doing"
    )
    inputs: List[ScriptInput] = Field(..., description="The inputs of the script")
    outputs: List[ScriptOutput] = Field(..., description="The outputs of the script")


class RunScriptByName(BaseModel):
    """
    Request to run a script.
    """
    inputs: Dict[str, Any] = Field(..., description="The inputs to pass to the script")
    script_name: str = Field(..., description="The name of the script to run")
