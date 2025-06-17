"""
Tooly API.
"""

from typing import List, Dict, Any
from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from maketools.services.code_executor import CodeExecutorService
from maketools.services.tool import ToolService
from maketools.schemas import MakeToolsContext

load_dotenv(".env")
# pylint: disable=wrong-import-position
from maketools.db.db import get_db
from maketools.agents.tester import test_code_with_ai
from maketools.services.conversation import ConversationService
from maketools.models.tool import Tool
from maketools.services.files import FileService
from maketools.models.conversation import Conversation
from maketools.schemas.tool import RunToolByName, ToolRead
from maketools.schemas.tester import TestResult
from maketools.controllers.base import (
    SendMessageRequest,
    get_tool,
    update_conversation_with_agent,
)

app = FastAPI()

WORKSPACE_ID = "local"


@app.post("/tools/{workspace_id}/upload")
async def post_upload_file(
    workspace_id: str, file: UploadFile = File(...)
):
    """
    Upload a file to the workspace.
    Args:
        workspace_id: The id of the workspace.
        file: The file to upload.
        session: The database session.
    Returns:
        The message.
    """
    await FileService.upload_file(workspace_id, file)
    return JSONResponse({"message": "File uploaded successfully"})

@app.delete("/tools/{workspace_id}/files/{file_path:path}")
async def delete_file(workspace_id: str, file_path: str):
    """
    Delete a file from the workspace.
    """
    await FileService.delete_file(workspace_id, file_path)
    return JSONResponse({"message": "File deleted successfully"})

@app.get("/tools/{workspace_id}/files")
async def get_files(workspace_id: str):
    """
    Get all files in the workspace.
    """
    return FileService.get_filepaths(workspace_id)

@app.post("/conversations/create")
async def post_create_conversation(
    request: SendMessageRequest, session: Session = Depends(get_db)
):
    """
    Create a new conversation and post a first message to it.
    Args:
        request: The request body.
        session: The database session.
    Returns:
        The conversation id.
    """
    conversation = await ConversationService.create_conversation(
        session, request.message
    )
    return JSONResponse({"conversation_id": conversation.id})


@app.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str, session: Session = Depends(get_db)):
    """
    Get a conversation.
    """
    conversation = await ConversationService.get_conversation(session, conversation_id)
    return conversation


@app.get("/conversations", response_model=List[Conversation])
async def get_conversations(session: Session = Depends(get_db)):
    """
    List all conversations.
    """
    conversations = await ConversationService.list_conversations(session)
    return conversations

@app.delete("/conversations/{conversation_id}", response_model=Conversation)
async def delete_conversation(conversation_id: str, session: Session = Depends(get_db)):
    """
    Delete a conversation.
    """
    await ConversationService.delete_conversation(session, conversation_id)
    return JSONResponse({"message": "Conversation deleted successfully"})

@app.post("/conversations/{conversation_id}/send")
async def post_send_message(
    conversation_id: str,
    request: SendMessageRequest,
    session: Session = Depends(get_db),
):
    """
    Send a message to the conversation.
    Args:
        conversation_id: The id of the conversation.
        request: The request body.
        session: The database session.
    """
    print(f"Sending message: {request.message}")
    await ConversationService.send_message(session, conversation_id, request.message)
    return JSONResponse({"message": "Message sent successfully"})


@app.get("/conversations/{conversation_id}/update")
async def sse_update_conversation(
    conversation_id: str, session: Session = Depends(get_db)
):
    """
    Update the tool with the agent response. Main loop to call the agent.
    Require to first post a message to the conversation with the /conversations/{conversation_id}/send or /conversations/create endpoint.
    Args:
        conversation_id: The id of the conversation.
        session: The database session.
    Returns:
        The event source response.
    """

    async def event_generator():
        async for event in update_conversation_with_agent(
            WORKSPACE_ID, conversation_id, session
        ):
            yield event

    return EventSourceResponse(event_generator())


@app.get("/tools/{tool_id}", response_model=ToolRead)
async def get_tool_by_id(tool_id: str, session: Session = Depends(get_db)):
    """
    Get a tool by id.
    Args:
        tool_id: The id of the tool.
        session: The database session.
    Returns:
        The tool.
    """
    tool = await get_tool(tool_id, session)
    return tool

@app.post("/tools/{tool_id}/test", response_model=TestResult)
async def post_test_tool(tool_id: str, session: Session = Depends(get_db)):
    """
    Test a tool.
    """
    test_result = await test_code_with_ai(MakeToolsContext(session=session, current_tool_id=tool_id, workspace_id=WORKSPACE_ID))
    return test_result

@app.get("/tools", response_model=List[ToolRead])
async def get_tools(session: Session = Depends(get_db)):
    """
    Get all tools.
    """
    return ToolService.list_tools(session)

@app.get("/tools_with_code", response_model=List[Tool])
async def get_tools_with_code(session: Session = Depends(get_db)):
    """
    Get all tools.
    """
    return ToolService.list_tools(session)

@app.post("/tools/run", response_model=Dict[str, Any])
async def run_tool(request: RunToolByName, session: Session = Depends(get_db)):
    """
    Run a tool.
    Args:
        request: The request body.
        session: The database session.
    Returns:
        The tool outputs.
    """
    return await CodeExecutorService.run_with_tool_name(session, WORKSPACE_ID, request.tool_name, request.inputs)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
