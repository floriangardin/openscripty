"""
Service for handling scripts.
"""

from typing import List
import traceback
from sqlalchemy.orm import Session
from fastapi import HTTPException
from scripty.models.script import (
    Script,
    ScriptORM,
)
from scripty.schemas.script import ScriptCreate, ScriptUpdate


class ScriptService:
    """
    Service for handling scripts.
    """

    @staticmethod
    def update_script(session: Session, script_id: str, script: ScriptUpdate) -> Script:
        """
        Update a script in the database.
        Args:
            script: The script to update.
        """
        try:
            print(f"Updating script: {script}")
            script_orm = (
                session.query(ScriptORM).filter(ScriptORM.id == script_id).first()
            )
            if not script_orm:
                raise ValueError("Script not found")
            # Update only fields that are not None in script (ScriptUpdate)
            for field, value in script.model_dump(
                exclude_unset=True, exclude_none=True
            ).items():
                if hasattr(script_orm, field):
                    setattr(script_orm, field, value)
            script_orm.touched = True
            session.commit()
            session.refresh(script_orm)
            return Script.model_validate(script_orm)
        except Exception as e:
            session.rollback()
            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail=f"Error updating script: {e}"
            ) from e

    @staticmethod
    def create_script(session: Session, script: ScriptCreate) -> Script:
        """
        Create a script in the database.
        """
        try:
            script_orm = ScriptORM(
            name=script.name,
            code=script.code,
            description=script.description,
            touched=True,
            )
            session.add(script_orm)
            session.commit()
            session.refresh(script_orm)
            return Script.model_validate(script_orm)
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500, detail=f"Error creating script: {e}"
            ) from e


    @staticmethod
    def get_script(session: Session, script_id: str) -> Script:
        """
        Get a script from the database.
        Args:
            session: The database session.
            script_id: The id of the script.
        """
        script_orm = session.query(ScriptORM).filter(ScriptORM.id == script_id).first()
        if not script_orm:
            raise HTTPException(status_code=404, detail="Script not found")
        return Script.model_validate(script_orm)

    @staticmethod
    def get_script_by_name(session: Session, script_name: str) -> Script:
        """
        Get a script from the database by name.
        """
        script_orm = session.query(ScriptORM).filter(ScriptORM.name == script_name).first()
        if not script_orm:
            raise HTTPException(status_code=404, detail="Script not found")
        return Script.model_validate(script_orm)
    
    @staticmethod
    def list_scripts(session: Session) -> List[Script]:
        """
        List all scripts.
        Args:
            session: The database session.
        Returns:
            A list of scripts.
        """
        script_orms = session.query(ScriptORM).filter(ScriptORM.touched == True).all()
        return [Script.model_validate(script_orm) for script_orm in script_orms]
