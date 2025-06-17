"""
Service for handling tools.
"""

from typing import List
import traceback
from sqlalchemy.orm import Session
from fastapi import HTTPException
from maketools.models.tool import (
    Tool,
    ToolORM,
)
from maketools.schemas.tool import ToolCreate, ToolUpdate

class ToolService:
    """
    Service for handling tools.
    """

    @staticmethod
    def update_tool(session: Session, tool_id: str, tool: ToolUpdate) -> Tool:
        """
        Update a tool in the database.
        Args:
            tool: The tool to update.
        """
        try:
            print(f"Updating tool: {tool}")
            tool_orm = (
                session.query(ToolORM).filter(ToolORM.id == tool_id).first()
            )
            if not tool_orm:
                raise ValueError("Tool not found")
            # Update only fields that are not None in tool (ToolUpdate)
            for field, value in tool.model_dump(
                exclude_unset=True, exclude_none=True
            ).items():
                if hasattr(tool_orm, field):
                    setattr(tool_orm, field, value)
            session.commit()
            session.refresh(tool_orm)
            return Tool.model_validate(tool_orm)
        except Exception as e:
            session.rollback()
            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail=f"Error updating tool: {e}"
            ) from e

    @staticmethod
    def create_tool(session: Session, tool: ToolCreate) -> Tool:
        """
        Create a tool in the database.
        """
        try:
            tool_orm = ToolORM(
            name=tool.name,
            code=tool.code,
            description=tool.description,
            )
            session.add(tool_orm)
            session.commit()
            session.refresh(tool_orm)
            return Tool.model_validate(tool_orm)
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500, detail=f"Error creating tool: {e}"
            ) from e


    @staticmethod
    def get_tool(session: Session, tool_id: str) -> Tool:
        """
        Get a tool from the database.
        Args:
            session: The database session.
            tool_id: The id of the tool.
        """
        tool_orm = session.query(ToolORM).filter(ToolORM.id == tool_id).first()
        if not tool_orm:
            raise HTTPException(status_code=404, detail="Tool not found")
        return Tool.model_validate(tool_orm)

    @staticmethod
    def get_tool_by_name(session: Session, tool_name: str) -> Tool:
        """
        Get a tool from the database by name.
        """
        tool_orm = session.query(ToolORM).filter(ToolORM.name == tool_name).first()
        if not tool_orm:
            raise HTTPException(status_code=404, detail="Tool not found")
        return Tool.model_validate(tool_orm)
    
    @staticmethod
    def list_tools(session: Session) -> List[Tool]:
        """
        List all tools.
        Args:
            session: The database session.
        Returns:
            A list of tools.
        """
        tool_orms = session.query(ToolORM).filter(ToolORM.touched).all()
        return [Tool.model_validate(tool_orm) for tool_orm in tool_orms]
