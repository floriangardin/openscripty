"""
The Pydantic model for the conversation.
"""
from dataclasses import dataclass
from typing import Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from maketools.models.base import Base


@dataclass
class ConversationORM(Base):
    """
    The SQLAlchemy mapped dataclass for the tool.
    """

    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    previous_response_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    last_agent_name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default=None
    )
    current_tool_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default=None
    )


class Conversation(BaseModel):
    """
    The Pydantic model for the conversation.
    """

    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="The id of the conversation")
    previous_response_id: Optional[str] = Field(
        ..., description="The id of the previous response"
    )
    current_tool_id: Optional[str] = Field(
        None, description="The id of the current tool"
    )
    user_prompt: str = Field(..., description="The user prompt")
    last_agent_name: Optional[str] = Field(
        None, description="The name of the last agent"
    )
