"""
Schemas for testing.
"""
from pydantic import BaseModel


class TestResult(BaseModel):
    """
    Result of a test.
    """
    success: bool
    details: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None


    @property
    def full_output(self) -> str | None:
        """
        Get the full output of the test.
        """
        result = ""
        if self.stdout:
            result += self.stdout
        if self.stderr:
            result += self.stderr
        return result