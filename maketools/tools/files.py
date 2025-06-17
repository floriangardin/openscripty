"""
This module contains the tools related to files handling.
"""

from typing import List
import os
import subprocess
import shlex
from agents import RunContextWrapper, function_tool
from maketools.schemas import MakeToolsContext
from maketools.services.files import FileService

# pylint: disable=unused-argument
def _cat_file_impl(filepath: str, line_start: int = 0, line_end: int = 200) -> str:
    if line_end - line_start > 200:
        return "Error: Maximum 200 lines of content"
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        return "\n".join(lines[line_start:line_end+1])


# pylint: disable=unused-argument
@function_tool
def cat_file(
    wrapper: RunContextWrapper[MakeToolsContext],
    filepath: str,
    line_start: int = 0,
    line_end: int = 200,
) -> str:
    """
    Cat a text file. (Maximum 1000 chars or 200 lines of content)
    Do not use with binary files.
    Args:
        filepath: The filepath of the file to cat.
        line_start: The line number to start from. (Default: 0)
        line_end: The line number to end at. (Default: 200)
    Returns:
        The content of the file.
    """
    return _cat_file_impl(os.path.join(FileService.get_file_directory(wrapper.context.workspace_id), filepath), 
                          line_start, line_end)

@function_tool
def list_files(wrapper: RunContextWrapper[MakeToolsContext]) -> List[str]:
    """
    List all files in the workspace.
    """
    return FileService.get_filepaths(wrapper.context.workspace_id)

def _run_bash_command_impl(command: str, cwd: str) -> str:
    # Disallow absolute paths and parent directory traversal
    tokens = shlex.split(command)
    for token in tokens:
        if token.startswith("/"):
            return "Error: Absolute paths are not allowed. Command rejected."
        if ".." in token:
            return "Error: Parent directory traversal is not allowed. Command rejected."
        if token.startswith("~"):
            return "Error: ~ is not allowed. Command rejected."
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, check=False, cwd=cwd
    )
    has_error = result.returncode != 0
    if has_error:
        return f"Error: {result.stderr}"
    return result.stdout


@function_tool
def run_bash_command(wrapper: RunContextWrapper[MakeToolsContext], command: str) -> str:
    """
    Run a bash command, restricted to the CONTAINER_DATA_DIRECTORY.
    Args:
        command: The command to run.
    Returns:
        The output of the command.
        If the command fails or is not allowed, returns the error message.
    """
    cwd = FileService.get_file_directory(wrapper.context.workspace_id)
    return _run_bash_command_impl(command, cwd)


@function_tool
def touch_file(filepath: str, content: str = "", mode="w") -> str:
    """
    Write content into a file.
    If the file does not exist, it will be created.
    If the file exists, it will be overwritten.
    Args:
        filepath: The filepath of the file to write to.
        content: The content of the file. (Default: "")
        mode: The mode to write the file in. (Values: "w" or "a") (Default: "w")
    Returns:
        The output of the command.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, mode, encoding="utf-8") as f:
        f.write(content)
    return f"File {filepath} created"
