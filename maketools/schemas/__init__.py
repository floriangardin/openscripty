"""
This module contains the schemas for the maketools api.
"""

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from maketools.models.conversation import Conversation, ConversationORM
from maketools.models.tool import Tool, ToolORM
from maketools.services.files import FileService


class MakeToolsContext(BaseModel):
    """
    Context passed to the LLM for the maketools api.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    session: Session
    current_tool_id: str | None = None
    current_conversation_id: str | None = None
    last_agent_name: str | None = None
    workspace_id: str | None = None
    filepaths: list[str] = []

    @property
    def current_conversation(self) -> Conversation:
        """
        Get the current conversation from the database.
        """
        conversation_orm = (
            self.session.query(ConversationORM)
            .filter(ConversationORM.id == self.current_conversation_id)
            .first()
        )
        return Conversation.model_validate(conversation_orm)

    @property
    def current_tool(self) -> Tool:
        """
        Get the current tool from the database.
        """
        tool_orm = (
            self.session.query(ToolORM)
            .filter(ToolORM.id == self.current_tool_id)
            .first()
        )
        return Tool.model_validate(tool_orm)

    def set_current_tool_id(self, value: str):
        """
        Set the current tool id, side effect: updates the database.
        """
        self.current_tool_id = value
        # Update the database
        conversation_orm = (
            self.session.query(ConversationORM)
            .filter(ConversationORM.id == self.current_conversation_id)
            .first()
        )
        if conversation_orm is None:
            raise ValueError("Conversation not found")
        conversation_orm.current_tool_id = value
        self.session.commit()

    def set_last_agent_name(self, value: str):
        """
        Set the last agent name, side effect: updates the database.
        """
        self.last_agent_name = value
        # Update the database
        conversation_orm = (
            self.session.query(ConversationORM)
            .filter(ConversationORM.id == self.current_conversation_id)
            .first()
        )
        if conversation_orm is None:
            raise ValueError("Conversation not found")
        conversation_orm.last_agent_name = value
        self.session.commit()


def get_context_from_db(
    session: Session, workspace_id: str, conversation_id: str
) -> MakeToolsContext:
    """
    Get the context from the database.
    Args:
        session: The database session.
        workspace_id: The id of the workspace.
        conversation_id: The id of the conversation.
    """
    conversation_orm = (
        session.query(ConversationORM)
        .filter(ConversationORM.id == conversation_id)
        .first()
    )
    if conversation_orm is None:
        raise ValueError("Conversation not found")
    return MakeToolsContext(
        session=session,
        workspace_id=workspace_id,
        current_conversation_id=conversation_id,
        last_agent_name=conversation_orm.last_agent_name,
        current_tool_id=conversation_orm.current_tool_id,
        filepaths=FileService.get_filepaths(workspace_id),
    )


__all__ = ["MakeToolsContext"]
