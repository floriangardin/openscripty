"""
The code executor tool.
"""
from agents import RunContextWrapper, function_tool
from maketools.schemas import MakeToolsContext
from maketools.services.code_executor import CodeExecutorService
import traceback
from typing import Dict, Any

@function_tool(strict_mode=False)
async def execute_code(ctx: RunContextWrapper[MakeToolsContext], inputs: Dict[str, Any]) -> str:
    """
    Execute the current tool code.
    Require to have generated the code first.
    Args:
        inputs: The inputs to pass to the code, must follow the openapi schema of the tool.
    """
    try:
        return await CodeExecutorService.run_code_with_inputs(ctx.context.current_tool,
                                                               ctx.context.workspace_id, 
                                                               inputs)
    except RuntimeError as e:
        traceback.print_exc()
        raise RuntimeError(f"Error executing code: {e}") from e
    except ValueError as e:
        traceback.print_exc()
        raise ValueError(f"Error parsing inputs: {e}") from e
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"Error executing code: {e}") from e
    

@function_tool(strict_mode=False)
async def execute_code_with_tool_name(ctx: RunContextWrapper[MakeToolsContext], tool_name: str, inputs: Dict[str, Any]) -> str:
    """
    Execute the code with the tool name.
    Args:
        tool_name: The name of the tool to execute, must exist in the database.
        inputs: The inputs to pass to the code, must follow the openapi schema of the tool.
    """
    return await CodeExecutorService.run_with_tool_name(ctx.context.session, ctx.context.workspace_id, tool_name, inputs)   