"""
The code executor tool.
"""
from agents import RunContextWrapper, function_tool
from scripty.schemas import ScriptyContext
from scripty.services.code_executor import CodeExecutorService
import traceback
from typing import Dict, Any

@function_tool(strict_mode=False)
async def execute_code(ctx: RunContextWrapper[ScriptyContext], inputs: Dict[str, Any]) -> str:
    """
    Execute the current script code.
    Require to have generated the code first.
    Args:
        inputs: The inputs to pass to the code, must follow the openapi schema of the script.
    """
    try:
        return await CodeExecutorService.run_code_with_inputs(ctx.context.current_script,
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