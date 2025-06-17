"""
This module contains the schemas for the maketools api.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ToolCreateNoCode(BaseModel):
    """
    Create a tool in the database.
    """
    name: str = Field(..., description="The name of the tool, named like a python function (snake case)")
    description: str = Field(
        ..., description="Full documentation of the tool, what it should be doing what are inputs and outputs"
    )

class ToolCreate(ToolCreateNoCode):
    """
    Create a tool in the database.
    """
    code: Optional[str] = Field(None, description="The code of the tool")

class ToolUpdateNoCode(ToolCreateNoCode):
    """
    Update a tool in the database.
    """

class ToolUpdate(ToolUpdateNoCode):
    """
    Update a tool in the database.
    """
    code: Optional[str] = Field(None, description="The code of the tool")


class ToolRead(BaseModel):
    """
    Read a tool from the database.
    """
    model_config = ConfigDict(from_attributes=True)
    name: str = Field(..., description="The name of the tool")
    description: str = Field(
        ..., description="Full documentation of the tool, what it should be doing"
    )
    inputs: dict | None = Field(
        None,
        description="The inputs of the tool, if it exists as an openapi schema",
    )
    outputs: dict | None = Field(
        None,
        description="The outputs of the tool, if it exists as an openapi schema",
    )


class RunToolByName(BaseModel):
    """
    Request to run a tool.
    """
    inputs: Dict[str, Any] = Field(..., description="The inputs to pass to the tool")
    tool_name: str = Field(..., description="The name of the tool to run")
