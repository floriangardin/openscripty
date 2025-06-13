# pylint: skip-file
import pytest
from unittest.mock import patch, MagicMock
from scripty.tools.files import _run_bash_command_impl


@patch("scripty.tools.files.subprocess.run")
def test_run_bash_command_absolute_path(mock_run):
    result = _run_bash_command_impl("cat /etc/passwd", "/allowed/directory")
    assert "Absolute paths are not allowed" in result
    mock_run.assert_not_called()


@patch("scripty.tools.files.subprocess.run")
def test_run_bash_command_parent_traversal(mock_run):
    result = _run_bash_command_impl("cat ../secret.txt", "/allowed/directory")
    assert "Parent directory traversal is not allowed" in result
    mock_run.assert_not_called()


@patch("scripty.tools.files.subprocess.run")
def test_run_bash_command_tilde(mock_run):
    result = _run_bash_command_impl("cat ~", "/allowed/directory")
    assert "~ is not allowed" in result
    mock_run.assert_not_called()


@patch("scripty.tools.files.subprocess.run")
def test_run_bash_command_tilde_in_command(mock_run):
    result = _run_bash_command_impl("LOCAL=~ & echo $LOCAL", "/allowed/directory")
    assert "~ is not allowed" in result
    mock_run.assert_not_called()


@patch("scripty.tools.files.subprocess.run")
def test_run_bash_command_valid_command(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "file content"
    mock_run.return_value = mock_result
    result = _run_bash_command_impl("cat file.txt", "/allowed/directory")
    assert result == "file content"
    mock_run.assert_called_once()


@patch("scripty.tools.files.subprocess.run")
def test_run_bash_command_error(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "error message"
    mock_run.return_value = mock_result
    result = _run_bash_command_impl("cat file.txt", "/allowed/directory")
    assert result == "Error: error message"
    mock_run.assert_called_once()
