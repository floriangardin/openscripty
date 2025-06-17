"""
This module contains the agents & agents factories for the maketools api.
"""

from typing import Callable

from agents import Agent

from maketools.schemas import MakeToolsContext
from .tool import tool_agent_factory, SCRIPT_AGENT_NAME
from .tester import test_code_with_ai, TEST_CODE_WITH_AI_NAME


class AgentRegistry:
    """
    A registry of tool agents.
    """

    def __init__(self):
        self._agent_factories = {}
        self._default_agent_factory = None

    def register(
        self, name: str, agent: Callable[[MakeToolsContext], Agent[MakeToolsContext]]
    ):
        """
        Register a tool agent.
        Args:
            name: The name of the tool agent.
            agent: The agent factory function.
        """
        self._agent_factories[name] = agent

    def set_default_agent_factory(
        self, agent_factory: Callable[[MakeToolsContext], Agent[MakeToolsContext]]
    ):
        """
        Set the default agent factory.
        Args:
            agent_factory: The agent factory function.
        """
        self._default_agent_factory = agent_factory

    def get_agent_factory(
        self, name: str
    ) -> Callable[[MakeToolsContext], Agent[MakeToolsContext]]:
        """
        Get a tool agent.
        Args:
            name: The name of the tool agent.
        """
        return self._agent_factories.get(name, self._default_agent_factory)


AgentRegistryInstance = AgentRegistry()

AgentRegistryInstance.register(SCRIPT_AGENT_NAME, tool_agent_factory)
AgentRegistryInstance.register(TEST_CODE_WITH_AI_NAME, test_code_with_ai)
AgentRegistryInstance.set_default_agent_factory(tool_agent_factory)

__all__ = ["AgentRegistryInstance"]
