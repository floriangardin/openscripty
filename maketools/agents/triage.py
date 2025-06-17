"""
This module contains the tool agent.
"""

from agents import Agent
from maketools.schemas import MakeToolsContext
from maketools.tools.files import cat_file, list_files
from maketools.tools.tool import say, create_or_update_tool, list_tools, switch_tool
from maketools.tools.code_executor import execute_code
from maketools.agents.code import create_code_with_ai
from maketools.agents.templates.template_manager import template_manager


TRIAGE_AGENT_NAME = "Triage agent"
INSTRUCTIONS_TEMPLATE = "triage"

def tool_agent_factory(context: MakeToolsContext) -> Agent[MakeToolsContext]:
    """
    Create a tool agent configured with the correct tools and instructions.
    """
    tools = [say,
             create_or_update_tool,
             create_code_with_ai,
             execute_code,
             cat_file,
             list_files,
             list_tools,
             switch_tool,
             ]
    tool_agent = Agent[MakeToolsContext](
        name=SCRIPT_AGENT_NAME,
        model="gpt-4o",
        handoff_description="An agent that helps create/update/execute a tool",
        tools=tools,
        handoffs=[tool_agent_factory(context)],
        instructions=lambda wrapper, agent: template_manager.render(INSTRUCTIONS_TEMPLATE, wrapper=wrapper, agent=agent),
    )
    return tool_agent
