"""
This module contains the script agent.
"""

from agents import Agent
from scripty.schemas import ScriptyContext
from scripty.tools.files import cat_file, list_files
from scripty.tools.script import say, create_or_update_script, list_scripts, switch_script
from scripty.tools.code_executor import execute_code
from scripty.agents.code import create_code_with_ai
from scripty.agents.templates.template_manager import template_manager


SCRIPT_AGENT_NAME = "Script handler"
INSTRUCTIONS_TEMPLATE = "script"

def script_agent_factory(context: ScriptyContext) -> Agent[ScriptyContext]:
    """
    Create a script agent configured with the correct tools and instructions.
    """
    tools = [say,
             create_or_update_script,
             create_code_with_ai,
             execute_code,
             cat_file,
             list_files,
             list_scripts,
             switch_script,
             ]
    script_agent = Agent[ScriptyContext](
        name=SCRIPT_AGENT_NAME,
        model="gpt-4o",
        handoff_description="An agent that helps create/update/execute a script",
        tools=tools,
        instructions=lambda wrapper, agent: template_manager.render(INSTRUCTIONS_TEMPLATE, wrapper=wrapper, agent=agent),
    )
    return script_agent
