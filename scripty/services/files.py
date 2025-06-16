"""
Service for handling files.
"""

import os
from fastapi import UploadFile


class FileService:
    """
    Service for handling files.
    """

    @staticmethod
    async def upload_file(workspace_id: str, file: UploadFile):
        """
        Upload a file to the scripty container.
        Args:
            workspace_id: The id of the conversation.
            file: The file to upload.
        """

        os.makedirs(FileService.get_file_directory(workspace_id), exist_ok=True)
        with open(
            os.path.join(FileService.get_file_directory(workspace_id), file.filename),
            "wb",
        ) as f:
            f.write(await file.read())

    @staticmethod
    async def delete_file(workspace_id: str, filepath: str):
        """
        Delete a file from the scripty container.
        Args:
            workspace_id: The id of the conversation.
            filepath: The filepath of the file.
        """
        os.remove(os.path.join(FileService.get_file_directory(workspace_id), filepath))

    @staticmethod
    def get_filepaths(workspace_id: str):
        """
        Get the filepaths for a script.
        Args:
            workspace_id: The id of the conversation.
        """
        try:
            return os.listdir(FileService.get_file_directory(workspace_id))
        except FileNotFoundError:
            return []

    @staticmethod
    def file_exists(workspace_id: str, filepath: str):
        """
        Check if a file exists in the scripty container.
        Args:
            workspace_id: The id of the conversation.
            filepath: The filepath of the file.
        """
        return os.path.exists(
            os.path.join(FileService.get_file_directory(workspace_id), str(filepath))
        )

    @staticmethod
    def get_file_directory(workspace_id: str):
        """
        Get the workspace directory
        Args:
            workspace_id: The id of the conversation.
        """
        return os.path.join(os.environ["CONTAINER_DATA_DIRECTORY"], workspace_id)
