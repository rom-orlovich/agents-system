"""
Sub-Agent Configuration
=======================

Manages sub-agent definitions for Claude CLI --agents flag.

Reference: https://code.claude.com/docs/en/sub-agents
"""

import json
from typing import Optional
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


def load_subagent_config(agent_dir: Path) -> Optional[str]:
    """
    Load sub-agent configuration for the given agent directory.

    Looks for subagents.json in the agent directory.
    Returns JSON string for --agents CLI flag, or None if not found.

    Example subagents.json:
    {
        "planning": {
            "description": "Analyze requirements and create implementation plans",
            "skills": ["analyze", "plan", "architecture"],
            "allowedTools": ["Read", "Glob", "Grep"]
        },
        "executor": {
            "description": "Implement code based on plans",
            "skills": ["implement", "test", "debug"],
            "allowedTools": ["Read", "Write", "Edit", "Bash"]
        }
    }

    Args:
        agent_dir: Directory containing agent configuration

    Returns:
        JSON string for --agents flag, or None if no configuration found
    """
    config_file = agent_dir / "subagents.json"

    if not config_file.exists():
        logger.debug("No sub-agent configuration found", agent_dir=str(agent_dir))
        return None

    try:
        config = json.loads(config_file.read_text())

        # Validate structure
        if not isinstance(config, dict):
            logger.error("Invalid sub-agent config: must be object", agent_dir=str(agent_dir))
            return None

        for name, definition in config.items():
            if not isinstance(definition, dict):
                logger.error(
                    "Invalid sub-agent definition: must be object",
                    agent_dir=str(agent_dir),
                    subagent=name
                )
                return None

        # Return as compact JSON string
        json_str = json.dumps(config, separators=(",", ":"))
        logger.info(
            "Loaded sub-agent configuration",
            agent_dir=str(agent_dir),
            subagents=list(config.keys())
        )
        return json_str

    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse sub-agent config",
            agent_dir=str(agent_dir),
            error=str(e)
        )
        return None
    except Exception as e:
        logger.error(
            "Failed to load sub-agent config",
            agent_dir=str(agent_dir),
            error=str(e)
        )
        return None


def get_default_subagents() -> str:
    """
    Get default sub-agent configuration for brain.

    This is used when no specific sub-agent config is found.

    Returns:
        JSON string with default sub-agents
    """
    default_config = {
        "planning": {
            "description": "Analyze requirements and create plans",
            "skills": ["analyze", "plan", "architecture", "design"],
            "allowedTools": ["Read", "Glob", "Grep"]
        },
        "implementation": {
            "description": "Implement code and features",
            "skills": ["implement", "code", "refactor"],
            "allowedTools": ["Read", "Write", "Edit", "Glob", "Grep"]
        },
        "testing": {
            "description": "Write and run tests",
            "skills": ["test", "validate", "qa"],
            "allowedTools": ["Read", "Write", "Edit", "Bash"]
        },
        "debugging": {
            "description": "Debug issues and fix bugs",
            "skills": ["debug", "fix", "troubleshoot"],
            "allowedTools": ["Read", "Edit", "Bash", "Glob", "Grep"]
        }
    }

    return json.dumps(default_config, separators=(",", ":"))
