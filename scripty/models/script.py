"""
This module contains the models for the scripty api.
"""

from enum import Enum
from typing import List, Optional, Union
import uuid
from dataclasses import dataclass
from pydantic import BaseModel, Field, ConfigDict

# --- SQLAlchemy mapped dataclasses ---
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Boolean,
    Text,
    ForeignKey,
    Enum as SQLAlchemyEnum,
)
from scripty.models.base import Base


class ArgumentType(str, Enum):
    """
    The type of the argument (for inputs and outputs).
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    FILE = "file"
    JSON = "json"


ArgumentTypeEnum = SQLAlchemyEnum(ArgumentType, name="argument_type")


def generate_uuid():
    """
    Generate a UUID.
    """
    return str(uuid.uuid4())


@dataclass
class ScriptInputORM(Base):
    """
    The SQLAlchemy mapped dataclass for the script input.
    """

    __tablename__ = "script_inputs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    script_id: Mapped[str] = mapped_column(
        String, ForeignKey("scripts.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[ArgumentType] = mapped_column(ArgumentTypeEnum, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    script: Mapped["ScriptORM"] = relationship(back_populates="inputs")


@dataclass
class ScriptOutputORM(Base):
    """
    The SQLAlchemy mapped dataclass for the script output.
    """

    __tablename__ = "script_outputs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    script_id: Mapped[str] = mapped_column(
        String, ForeignKey("scripts.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[ArgumentType] = mapped_column(ArgumentTypeEnum, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    filepath: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    script: Mapped["ScriptORM"] = relationship(back_populates="outputs")


# pylint: disable=too-many-instance-attributes
@dataclass
class ScriptORM(Base):
    """
    The SQLAlchemy mapped dataclass for the script.
    """

    __tablename__ = "scripts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    code: Mapped[str] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    test_code: Mapped[str] = mapped_column(Text, nullable=True)
    touched: Mapped[bool] = mapped_column(Boolean, default=False)
    inputs: Mapped[list[ScriptInputORM]] = relationship(
        "ScriptInputORM", back_populates="script", cascade="all, delete-orphan"
    )
    outputs: Mapped[list[ScriptOutputORM]] = relationship(
        "ScriptOutputORM", back_populates="script", cascade="all, delete-orphan"
    )


class ScriptInput(BaseModel):
    """
    The Pydantic model for the script input.
    """

    model_config = ConfigDict(from_attributes=True)
    name: str = Field(..., description="The name of the input in python snake case")
    type: ArgumentType = Field(..., description="The type of the input")
    description: str = Field(..., description="Documentation of the input")
    value: Union[str, int, float, bool] | None = Field(
        None,
        description="The value of the input. Will be used as the inputs of the script execution."
        "For JSON inputs, put proper JSON string.",
    )


class ScriptOutput(BaseModel):
    """
    The Pydantic model for the script output.
    """

    model_config = ConfigDict(from_attributes=True)
    name: str = Field(..., description="The name of the output in python snake case")
    type: ArgumentType = Field(..., description="The type of the output")
    description: str = Field(..., description="Documentation of the output")
    filepath: str = Field(
        None,
        description="The filepath of the output, required for files."
        "Put empty string for non-file outputs.",
    )


class Script(BaseModel):
    """
    The Pydantic model for the script.
    """

    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="The id of the script")
    name: str = Field(..., description="The name of the script")
    code: str | None = Field(
        None,
        description="The code of the script, if it exists",
    )
    test_code: str | None = Field(
        None,
        description="The test code of the script, if it exists",
    )
    description: str = Field(
        ..., description="Full documentation of the script, what it should be doing"
    )
    inputs: List[ScriptInput] = Field(
        ...,
        description="The inputs of the script (arguments that will be passed to the code)",
    )
    outputs: List[ScriptOutput] = Field(
        ...,
        description="The outputs of the script (arguments that will be returned by the code)",
    )
    touched: bool = Field(
        False, description="Whether the script has been touched by the user"
    )

    @property
    def code_generated(self) -> bool:
        """
        Whether the script has been touched by the user and has a code generated.
        """
        return self.code is not None

    def to_openapi_schema(self) -> dict:
        """
        Convert the script inputs to an OpenAPI schema.
        
        Returns:
            dict: The OpenAPI schema for the script inputs.
        """
        properties = {}
        required = []
        
        for input_field in self.inputs:
            # Convert ArgumentType to OpenAPI type
            type_mapping = {
                ArgumentType.STRING: "string",
                ArgumentType.INTEGER: "integer",
                ArgumentType.FLOAT: "number",
                ArgumentType.BOOLEAN: "boolean",
                ArgumentType.LIST: "array",
                ArgumentType.DICT: "object",
                ArgumentType.FILE: "string",
                ArgumentType.JSON: "object"
            }
            
            openapi_type = type_mapping[input_field.type]
            
            # Create property schema
            property_schema = {
                "type": openapi_type,
                "description": input_field.description,
                "title": input_field.name.replace("_", " ").title()
            }
            
            # Add format for file type
            if input_field.type == ArgumentType.FILE:
                property_schema["format"] = "binary"
            
            # Add items for list type
            if input_field.type == ArgumentType.LIST:
                property_schema["items"] = {"type": "string"}
            
            properties[input_field.name] = property_schema
            required.append(input_field.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "title": self.name.replace("_", " ").title()
        }
