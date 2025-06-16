"""
This module contains the models for the scripty api.
"""

from enum import Enum
from typing import List, Optional, Union
import uuid
from dataclasses import dataclass
from pydantic import BaseModel, Field, ConfigDict

# --- SQLAlchemy mapped dataclasses ---
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    JSON,
    String,
    Boolean,
    Text,
)
from scripty.models.base import Base

def generate_uuid():
    """
    Generate a UUID.
    """
    return str(uuid.uuid4())


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
    docstring: Mapped[str] = mapped_column(Text, nullable=True)
    inputs: Mapped[JSON] = mapped_column(JSON, nullable=True)
    outputs: Mapped[JSON] = mapped_column(JSON, nullable=True)
    touched: Mapped[bool] = mapped_column(Boolean, default=False)

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
    inputs: dict | None = Field(
        None,
        description="The inputs of the script, if it exists as an openapi schema",
    )
    outputs: dict | None = Field(
        None,
        description="The outputs of the script, if it exists as an openapi schema",
    )
    docstring: str | None = Field(
        None,
        description="The docstring of the script, if it exists",
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
