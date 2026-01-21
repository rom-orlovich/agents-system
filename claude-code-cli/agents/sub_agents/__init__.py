"""
Sub-agents auto-discovery.

This module automatically discovers and registers all sub-agents
in this directory.
"""

import logging
import importlib
import inspect
from pathlib import Path
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from core.agent_registry import AgentRegistry
    from core.agent_base import BaseAgent

logger = logging.getLogger(__name__)


def discover_agent_modules() -> List[str]:
    """
    Discover all agent modules in this directory.

    Returns:
        List of module names (without .py extension)
    """
    agents_dir = Path(__file__).parent
    agent_files = agents_dir.glob("*_agent.py")

    modules = []
    for file in agent_files:
        module_name = file.stem  # Remove .py extension
        modules.append(module_name)

    logger.debug(f"Discovered agent modules: {modules}")
    return modules


def auto_register_agents(registry: "AgentRegistry") -> None:
    """
    Auto-discover and register all agents.

    Args:
        registry: AgentRegistry instance to register agents with
    """
    from core.agent_base import BaseAgent

    agent_modules = discover_agent_modules()

    for module_name in agent_modules:
        try:
            # Import module
            module = importlib.import_module(f"sub_agents.{module_name}")

            # Find all BaseAgent subclasses
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Skip the base class itself
                if obj is BaseAgent:
                    continue

                # Check if it's a subclass of BaseAgent
                if issubclass(obj, BaseAgent):
                    # Instantiate and register
                    agent = obj()
                    registry.register(agent)

        except Exception as e:
            logger.error(f"Failed to load agent module '{module_name}': {e}")
            logger.exception(e)


__all__ = [
    "auto_register_agents",
    "discover_agent_modules",
]
