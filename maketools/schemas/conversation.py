"""
The Pydantic model for the conversation.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class ConversationRead(BaseModel):
    """
    The Pydantic model for the conversation read.
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

class ConversationCreate(BaseModel):
    """
    The Pydantic model for the conversation create.
    """

    user_prompt: str = Field(..., description="The user prompt")