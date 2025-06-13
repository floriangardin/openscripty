"""
The code executor tool.
"""
from agents import RunContextWrapper, function_tool
from scripty.schemas import ScriptyContext
from scripty.services.code_executor import CodeExecutorService
import traceback

@function_tool
async def execute_code(ctx: RunContextWrapper[ScriptyContext]) -> str:
    """
    Execute the current script code.
    Require to have generated the code first.
    """
    try:
        return await CodeExecutorService.run_code(ctx.context.current_script, ctx.context.workspace_id)
    except RuntimeError as e:
        traceback.print_exc()
        raise RuntimeError(f"Error executing code: {e}") from e
    except ValueError as e:
        traceback.print_exc()
        raise ValueError(f"Error parsing inputs: {e}") from e
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"Error executing code: {e}") from e
    
@function_tool
async def call_tool(ctx: RunContextWrapper[ScriptyContext], tool_name: str, inputs: dict[str, Any]) -> str:
    """
    Call a tool with the given inputs.
    """
    return await CodeExecutorService.call_tool(ctx.context.current_script, tool_name, inputs)


@function_tool
async def run_test(ctx: RunContextWrapper[ScriptyContext]) -> str:
    """
    Run the tests for the current script.
    """
    return await CodeExecutorService.run_test(ctx.context.current_script, ctx.context.workspace_id)