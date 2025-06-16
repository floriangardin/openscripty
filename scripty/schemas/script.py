"""
This module contains the schemas for the scripty api.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ScriptCreateNoCode(BaseModel):
    """
    Create a script in the database.
    """
    name: str = Field(..., description="The name of the script, named like a python function (snake case)")
    description: str = Field(
        ..., description="Full documentation of the script, what it should be doing what are inputs and outputs"
    )

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
    inputs: dict | None = Field(
        None,
        description="The inputs of the script, if it exists as an openapi schema",
    )
    outputs: dict | None = Field(
        None,
        description="The outputs of the script, if it exists as an openapi schema",
    )


class RunScriptByName(BaseModel):
    """
    Request to run a script.
    """
    inputs: Dict[str, Any] = Field(..., description="The inputs to pass to the script")
    script_name: str = Field(..., description="The name of the script to run")
