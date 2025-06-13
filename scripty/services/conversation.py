"""
Service for handling conversations.
"""

from typing import List
from sqlalchemy.orm import Session
from scripty.models.conversation import Conversation, ConversationORM


class ConversationService:
    """
    Service for handling conversations.
    """

    @staticmethod
    async def create_conversation(session: Session, user_prompt: str) -> Conversation:
        """
        Create a new conversation.
        """
        conversation_orm = ConversationORM(
            user_prompt=user_prompt,
            last_agent_name=None,
        )
        session.add(conversation_orm)
        session.commit()
        conversation = Conversation.model_validate(conversation_orm)
        return conversation

    @staticmethod
    async def send_message(
        session: Session, conversation_id: str, message: str
    ) -> None:
        """
        Set the current user prompt.
        It's used because we use a POST request to send the full prompt before getting response with StreamingResponse.
        Args:
            session: The database session.
            conversation_id: The id of the conversation.
            message: The message to send to the script.
        """
        script_orm = (
            session.query(ConversationORM)
            .filter(ConversationORM.id == conversation_id)
            .first()
        )
        if not script_orm:
            raise ValueError("Script not found")
        script_orm.user_prompt = message
        session.commit()

    @staticmethod
    async def get_conversation(session: Session, conversation_id: str) -> Conversation:
        """
        Get a conversation.
        """
        conversation_orm = (
            session.query(ConversationORM)
            .filter(ConversationORM.id == conversation_id)
            .first()
        )
        return Conversation.model_validate(conversation_orm)
   
    @staticmethod
    async def list_conversations(session: Session) -> List[Conversation]:
        """
        List all conversations.
        """
        conversations_orm = session.query(ConversationORM).all()
        return [Conversation.model_validate(conversation_orm) for conversation_orm in conversations_orm]
 
    @staticmethod
    async def delete_conversation(session: Session, conversation_id: str) -> None:
        """
        Delete a conversation.
        """
        session.query(ConversationORM).filter(ConversationORM.id == conversation_id).delete()
        session.commit()

    @staticmethod
    def update_conversation_with_agent_response(
        session: Session,
        conversation_id: str,
        previous_response_id: str,
        last_agent_name: str,
    ) -> Conversation:
        """
        Update the script with the agent response.
        Args:
            session: The database session.
            conversation_id: The id of the script.
            previous_response_id: The id of the previous response.
            last_agent_name: The name of the last agent.
        """
        conversation_orm = (
            session.query(ConversationORM)
            .filter(ConversationORM.id == conversation_id)
            .first()
        )
        if not conversation_orm:
            raise ValueError("Script not found")
        conversation_orm.previous_response_id = previous_response_id
        conversation_orm.last_agent_name = last_agent_name
        conversation_orm.touched = True
        session.commit()
        session.refresh(conversation_orm)
        return Conversation.model_validate(conversation_orm)
