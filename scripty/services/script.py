"""
Service for handling scripts.
"""

from typing import List
import traceback
from sqlalchemy.orm import Session
from fastapi import HTTPException
from scripty.models.script import (
    ArgumentType,
    Script,
    ScriptORM,
    ScriptInputORM,
    ScriptOutputORM,
)
from scripty.schemas.script import ScriptCreate, ScriptRead, ScriptUpdate
from scripty.services.files import FileService


class ScriptService:
    """
    Service for handling scripts.
    """

    @staticmethod
    def _check_input_and_output_filepaths_different(
        session: Session, script: ScriptUpdate
    ) -> None:
        """
        Check if the input and output filepaths are different.
        It's because inputs and outputs are located in the same directory.
        Args:
            session: The database session.
            script: The script to check.
        """
        for input in script.inputs:
            if input.value is not None and input.type == ArgumentType.FILE:
                if input.value in [output.filepath for output in script.outputs]:
                    raise ValueError("Input and output filepaths cannot be the same")

    @staticmethod
    def _check_file_input_exists(
        session: Session, script: ScriptUpdate, script_id: str
    ) -> None:
        """
        Check if the file input exists.
        Args:
            session: The database session.
            script: The script to check.
            script_id: The id of the script.
        """
        for input in script.inputs:
            if input.value is not None and input.type == ArgumentType.FILE:
                if not FileService.file_exists(script_id, input.value):
                    raise ValueError(f"File {input.value} not found")

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
            ScriptService._check_input_and_output_filepaths_different(session, script)
            if not script_orm:
                raise ValueError("Script not found")
            # Update only fields that are not None in script (ScriptUpdate)
            for field, value in script.model_dump(
                exclude_unset=True, exclude_none=True
            ).items():
                if field == "inputs" and value is not None:
                    script_orm.inputs.clear()
                    for inp in value:
                        input_orm = ScriptInputORM(
                            script_id=script_orm.id,
                            name=inp["name"],
                            type=inp["type"],
                            description=inp["description"],
                            value=(
                                str(inp["value"]) if inp.get("value") is not None else None
                            ),
                        )
                        script_orm.inputs.append(input_orm)
                elif field == "outputs" and value is not None:
                    script_orm.outputs.clear()
                    for out in value:
                        output_orm = ScriptOutputORM(
                            script_id=script_orm.id,
                            name=out["name"],
                            type=out["type"],
                            description=out["description"],
                            filepath=out["filepath"],
                        )
                        script_orm.outputs.append(output_orm)
                elif hasattr(script_orm, field):
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
            inputs=[
                ScriptInputORM(
                    name=inp.name,
                    type=inp.type,
                    description=inp.description,
                    value=str(inp.value) if inp.value is not None else None,
                )
                for inp in script.inputs
            ],
            outputs=[
                ScriptOutputORM(
                    name=out.name,
                    type=out.type,
                    description=out.description,
                    filepath=out.filepath,
                )
                for out in script.outputs
                ],
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
        script_orms = session.query(ScriptORM).all()
        return [Script.model_validate(script_orm) for script_orm in script_orms]
