"""Template loader for webhook prompts.

Loads prompt templates from separate files instead of embedding them in YAML config.
Supports variable substitution using {{placeholder}} syntax.
"""
from pathlib import Path
from typing import Dict, Optional
import structlog
import re

logger = structlog.get_logger()


class TemplateLoader:
    """Load and render prompt templates from files."""

    def __init__(self, templates_dir: Path):
        """
        Initialize template loader.

        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = templates_dir
        self._cache: Dict[str, str] = {}

    def load_template(self, template_name: str) -> Optional[str]:
        """
        Load template from file.

        Args:
            template_name: Name of template (without extension)

        Returns:
            Template content or None if not found
        """
        if template_name in self._cache:
            return self._cache[template_name]

        template_path = self.templates_dir / f"{template_name}.md"

        if not template_path.exists():
            logger.warning(
                "template_not_found",
                template=template_name,
                path=str(template_path)
            )
            return None

        try:
            with open(template_path, 'r') as f:
                content = f.read()

            self._cache[template_name] = content

            logger.debug(
                "template_loaded",
                template=template_name,
                size=len(content)
            )

            return content

        except Exception as e:
            logger.error(
                "template_load_error",
                template=template_name,
                error=str(e)
            )
            return None

    def render_template(self, template_content: str, variables: Dict[str, any]) -> str:
        """
        Render template by replacing {{variables}} with actual values.

        Args:
            template_content: Template string with {{placeholders}}
            variables: Dictionary of variable values

        Returns:
            Rendered template
        """
        result = template_content

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))

        return result

    def load_and_render(self, template_name: str, variables: Dict[str, any]) -> Optional[str]:
        """
        Load template from file and render with variables.

        Args:
            template_name: Name of template file (without extension)
            variables: Dictionary of variable values

        Returns:
            Rendered template or None if template not found
        """
        template = self.load_template(template_name)
        if not template:
            return None

        return self.render_template(template, variables)

    def clear_cache(self):
        """Clear the template cache."""
        self._cache.clear()


def get_template_loader(webhook_name: str) -> TemplateLoader:
    """
    Get template loader for a webhook.

    Args:
        webhook_name: Name of webhook (github, jira, slack)

    Returns:
        TemplateLoader instance
    """
    base_path = Path(__file__).parent.parent / webhook_name / "prompts"
    base_path.mkdir(exist_ok=True)
    return TemplateLoader(base_path)


class BrainOrchestrator:
    """
    Brain agent orchestrator - selects appropriate sub-agent from .claude/agents/
    """

    def __init__(self, agents_dir: Path = None):
        """
        Initialize brain orchestrator.

        Args:
            agents_dir: Directory containing agent definitions (default: .claude/agents/)
        """
        if agents_dir is None:
            # Default to .claude/agents/ relative to project root
            agents_dir = Path(__file__).parent.parent.parent.parent / ".claude" / "agents"

        self.agents_dir = agents_dir
        self._available_agents = self._discover_agents()

    def _discover_agents(self) -> Dict[str, Path]:
        """Discover available agents in .claude/agents/ directory."""
        agents = {}

        if not self.agents_dir.exists():
            logger.warning("agents_dir_not_found", path=str(self.agents_dir))
            return agents

        for agent_file in self.agents_dir.glob("*.md"):
            agent_name = agent_file.stem
            agents[agent_name] = agent_file

        logger.info("agents_discovered", count=len(agents), agents=list(agents.keys()))

        return agents

    def select_agent(self, command: str, context: Dict[str, any]) -> Optional[str]:
        """
        Select appropriate sub-agent based on command and context.

        Args:
            command: Command name (e.g., 'analyze', 'plan', 'fix')
            context: Context dictionary with task details

        Returns:
            Agent name or None if no suitable agent found
        """
        # Map commands to agents
        command_to_agent = {
            "analyze": "planning",
            "plan": "planning",
            "fix": "executor",
            "execute": "executor",
            "implement": "executor",
            "review": "github-pr-review",
            "verify": "verifier",
        }

        agent_name = command_to_agent.get(command.lower())

        if agent_name and agent_name in self._available_agents:
            logger.info(
                "agent_selected",
                command=command,
                agent=agent_name
            )
            return agent_name

        # Default to planning agent
        logger.warning(
            "no_agent_match_using_default",
            command=command,
            default="planning"
        )
        return "planning"

    def get_available_agents(self) -> list[str]:
        """Get list of available agent names."""
        return list(self._available_agents.keys())


# Global brain orchestrator instance
brain = BrainOrchestrator()
