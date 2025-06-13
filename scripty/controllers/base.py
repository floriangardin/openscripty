"""
The base controller.
"""

from pydantic import BaseModel
import json
from sqlalchemy.orm import Session
from agents import Runner, ItemHelpers
from scripty.models.script import Script
from scripty.services.script import ScriptService
from scripty.schemas import ScriptyContext, get_context_from_db
from scripty.services.conversation import ConversationService
from scripty.agents import AgentRegistryInstance


def serialize_output(output) -> str:
    """
    Robust serialization for various output types.
    Handles dicts, strings, and Pydantic objects.
    """
    if isinstance(output, str):
        return output
    elif isinstance(output, dict):
        return json.dumps(output)
    elif hasattr(output, 'model_dump'):  # Pydantic v2
        return json.dumps(output.model_dump())
    elif hasattr(output, 'dict'):  # Pydantic v1
        return json.dumps(output.dict())
    else:
        # Fallback: try to convert to string
        try:
            return json.dumps(output)
        except TypeError:
            return str(output)


class CreateScriptRequest(BaseModel):
    message: str


class SendMessageRequest(BaseModel):
    message: str


async def get_script(script_id: str, session: Session) -> Script:
    """
    Get a script by id.
    Args:
        script_id: The id of the script.
        session: The database session.
    Returns:
        The script.
    """
    return ScriptService.get_script(session, script_id)


async def update_conversation_with_agent(
    workspace_id: str, conversation_id: str, session: Session
):
    """
    Update the conversation with the agent.
    Args:
        workspace_id: The id of the workspace.
        conversation_id: The id of the conversation.
        session: The database session.
    Returns:
        The conversation.
    """
    context: ScriptyContext = get_context_from_db(
        session, workspace_id, conversation_id
    )
    agent_factory = AgentRegistryInstance.get_agent_factory(context.last_agent_name)
    agent = agent_factory(context)
    result = Runner.run_streamed(
        agent,
        input=context.current_conversation.user_prompt,
        previous_response_id=context.current_conversation.previous_response_id,
        context=context,
        max_turns=20,
    )
    current_tool_name = None
    NEWLINE = "<br>"
    async for event in result.stream_events():
        # We'll ignore the raw responses event deltas
        if event.type == "raw_response_event":
            continue
        # When the agent updates, yield that
        elif event.type == "agent_updated_stream_event":
            data = {"event": "agent_updated", "data": event.new_agent.name}
            yield data
            continue
        # When items are generated, yield them
        elif event.type == "run_item_stream_event":
            if event.item.type == "tool_call_item":
                current_tool_name = event.item.raw_item.name
                if current_tool_name != 'say':
                    yield {"event": "tool_call", "data": current_tool_name}
                else:
                    yield {"event": "message_output", "data": event.item.raw_item.replace('\n', NEWLINE)}
            elif event.item.type == "tool_call_output_item":
                if current_tool_name == 'say':
                    pass
                else:
                    yield {"event": "tool_call_output", "data": serialize_output(event.item.output).replace('\n', NEWLINE)}
            elif event.item.type == "message_output_item":
                yield {"event": "message_output", "data": ItemHelpers.text_message_output(event.item).replace('\n', NEWLINE)}
            else:
                pass  # Ignore other event types

    previous_response_id = result.last_response_id
    last_agent_name = result.last_agent.name
    conversation = ConversationService.update_conversation_with_agent_response(
        session, conversation_id, previous_response_id, last_agent_name
    )
    yield {"event": "conversation_updated", "data": conversation}
    yield {"event": "end", "data": ""}



def create_tests(workspace_id: str, script_id: str, session: Session):
    """
    Create tests for a script.
    """
    script = ScriptService.get_script(session, script_id)
    