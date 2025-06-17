"""
This module contains the models for the maketools api.
"""

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
from maketools.models.base import Base

def generate_uuid():
    """
    Generate a UUID.
    """
    return str(uuid.uuid4())


# pylint: disable=too-many-instance-attributes
@dataclass
class ToolORM(Base):
    """
    The SQLAlchemy mapped dataclass for the tool.
    """

    __tablename__ = "tools"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    code: Mapped[str] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    test_code: Mapped[str] = mapped_column(Text, nullable=True)
    docstring: Mapped[str] = mapped_column(Text, nullable=True)
    inputs: Mapped[JSON] = mapped_column(JSON, nullable=True)
    outputs: Mapped[JSON] = mapped_column(JSON, nullable=True)
    touched: Mapped[bool] = mapped_column(Boolean, default=False)

class Tool(BaseModel):
    """
    The Pydantic model for the tool.
    """

    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="The id of the tool")
    name: str = Field(..., description="The name of the tool")
    code: str | None = Field(
        None,
        description="The code of the tool, if it exists",
    )
    test_code: str | None = Field(
        None,
        description="The test code of the tool, if it exists",
    )
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
    docstring: str | None = Field(
        None,
        description="The docstring of the tool, if it exists",
    )
    touched: bool = Field(
        False, description="Whether the tool has been touched by the user"
    )

    @property
    def code_generated(self) -> bool:
        """
        Whether the tool has been touched by the user and has a code generated.
        """
        return self.code is not None
