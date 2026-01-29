"""Test template loading from separate files."""
import pytest
from pathlib import Path
from api.webhooks.common.template_loader import TemplateLoader, BrainOrchestrator, get_template_loader
from api.webhooks.common.utils import get_template_content, load_webhook_config_from_yaml


class TestTemplateLoader:
    """Test TemplateLoader class."""

    def test_template_loader_loads_analyze_template(self):
        """Test that template loader can load analyze template."""
        loader = get_template_loader("github")
        template = loader.load_template("analyze")

        assert template is not None
        assert "Analyze GitHub Issue/PR" in template
        assert "{{issue.number}}" in template
        assert "{{repository.full_name}}" in template

    def test_template_loader_loads_plan_template(self):
        """Test that template loader can load plan template."""
        loader = get_template_loader("github")
        template = loader.load_template("plan")

        assert template is not None
        assert "Create Implementation Plan" in template
        assert "{{issue.key}}" in template or "{{issue.number}}" in template

    def test_template_loader_returns_none_for_missing_template(self):
        """Test that template loader returns None for missing template."""
        loader = get_template_loader("github")
        template = loader.load_template("nonexistent")

        assert template is None

    def test_template_loader_caches_templates(self):
        """Test that template loader caches loaded templates."""
        loader = get_template_loader("github")

        template1 = loader.load_template("analyze")
        template2 = loader.load_template("analyze")

        assert template1 == template2
        assert "analyze" in loader._cache

    def test_template_loader_renders_variables(self):
        """Test that template loader can render variables."""
        loader = get_template_loader("github")
        template = "Hello {{name}}, you have {{count}} messages."
        variables = {"name": "Alice", "count": 5}

        result = loader.render_template(template, variables)

        assert result == "Hello Alice, you have 5 messages."

    def test_template_loader_load_and_render(self):
        """Test load_and_render convenience method."""
        loader = get_template_loader("github")
        variables = {
            "issue.number": "123",
            "repository.full_name": "owner/repo",
            "issue.title": "Test Issue",
            "_user_content": "Please analyze this",
            "comment.body": "This is a test",
            "event_type": "issue"
        }

        result = loader.load_and_render("analyze", variables)

        assert result is not None
        assert "123" in result or "issue" in result.lower()


class TestBrainOrchestrator:
    """Test BrainOrchestrator class."""

    def test_brain_orchestrator_selects_planning_for_analyze(self):
        """Test that brain orchestrator selects planning agent for analyze command."""
        brain = BrainOrchestrator()
        context = {"command": "analyze", "source": "github"}

        agent = brain.select_agent("analyze", context)

        assert agent == "planning"

    def test_brain_orchestrator_selects_executor_for_fix(self):
        """Test that brain orchestrator selects executor agent for fix command."""
        brain = BrainOrchestrator()
        context = {"command": "fix", "source": "github"}

        agent = brain.select_agent("fix", context)

        assert agent == "executor"

    def test_brain_orchestrator_defaults_to_planning(self):
        """Test that brain orchestrator defaults to planning for unknown commands."""
        brain = BrainOrchestrator()
        context = {"command": "unknown", "source": "github"}

        agent = brain.select_agent("unknown", context)

        assert agent == "planning"

    def test_brain_orchestrator_gets_available_agents(self):
        """Test that brain orchestrator can list available agents."""
        brain = BrainOrchestrator()
        agents = brain.get_available_agents()

        assert isinstance(agents, list)


class TestGetTemplateContent:
    """Test get_template_content helper function."""

    def test_get_template_content_from_file(self):
        """Test getting template content from file."""
        config_path = Path(__file__).parent.parent.parent / "api" / "webhooks" / "github" / "config.yaml"
        config = load_webhook_config_from_yaml(config_path)

        assert config is not None
        assert len(config.commands) > 0

        analyze_command = next(cmd for cmd in config.commands if cmd.name == "analyze")

        template_content = get_template_content(analyze_command, "github")

        assert template_content is not None
        assert "Analyze GitHub Issue/PR" in template_content
        assert "{{issue.number}}" in template_content

    def test_get_template_content_supports_inline_prompt(self):
        """Test that get_template_content still supports inline prompt_template."""
        from shared.machine_models import WebhookCommand

        command = WebhookCommand(
            name="test",
            target_agent="planning",
            prompt_template="This is an inline template with {{variable}}",
            requires_approval=False
        )

        template_content = get_template_content(command, "github")

        assert template_content == "This is an inline template with {{variable}}"

    def test_get_template_content_prefers_template_file(self):
        """Test that template_file is used if both are present."""
        from shared.machine_models import WebhookCommand

        command = WebhookCommand(
            name="test",
            target_agent="planning",
            prompt_template="This should not be used",
            template_file="analyze",
            requires_approval=False
        )

        template_content = get_template_content(command, "github")

        assert template_content is not None
        assert "This should not be used" not in template_content
        assert "Analyze GitHub Issue/PR" in template_content


class TestAllWebhookTemplates:
    """Test that all webhook templates exist."""

    def test_all_github_templates_exist(self):
        """Test that all GitHub command templates exist."""
        config_path = Path(__file__).parent.parent.parent / "api" / "webhooks" / "github" / "config.yaml"
        config = load_webhook_config_from_yaml(config_path)

        assert config is not None

        for command in config.commands:
            if command.template_file:
                template_content = get_template_content(command, "github")
                assert template_content is not None, f"Template for {command.name} should exist"

    def test_all_jira_templates_exist(self):
        """Test that all Jira command templates exist."""
        config_path = Path(__file__).parent.parent.parent / "api" / "webhooks" / "jira" / "config.yaml"
        config = load_webhook_config_from_yaml(config_path)

        assert config is not None

        for command in config.commands:
            if command.template_file:
                template_content = get_template_content(command, "jira")
                assert template_content is not None, f"Template for {command.name} should exist"

    def test_all_slack_templates_exist(self):
        """Test that all Slack command templates exist."""
        config_path = Path(__file__).parent.parent.parent / "api" / "webhooks" / "slack" / "config.yaml"
        config = load_webhook_config_from_yaml(config_path)

        assert config is not None

        for command in config.commands:
            if command.template_file:
                template_content = get_template_content(command, "slack")
                assert template_content is not None, f"Template for {command.name} should exist"
