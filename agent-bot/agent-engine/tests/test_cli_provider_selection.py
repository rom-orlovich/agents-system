"""Tests for CLI provider selection business logic.

Tests how agent types map to CLI providers and models.
"""

from unittest.mock import MagicMock


COMPLEX_AGENTS = ["planning", "consultation", "question_asking", "brain"]
EXECUTION_AGENTS = ["executor", "github-issue-handler", "jira-code-plan"]


def get_model_for_agent(
    agent_type: str,
    cli_provider: str = "claude",
    settings: MagicMock | None = None,
) -> str:
    """Get the appropriate model for an agent type."""
    if settings is None:
        settings = MagicMock()
        settings.cli_provider = cli_provider
        settings.claude_model_complex = "opus"
        settings.claude_model_execution = "sonnet"
        settings.cursor_model_complex = "claude-sonnet-4.5"
        settings.cursor_model_execution = "composer-1"

    is_complex_task = agent_type.lower() in COMPLEX_AGENTS

    if settings.cli_provider == "cursor":
        return (
            settings.cursor_model_complex
            if is_complex_task
            else settings.cursor_model_execution
        )
    elif settings.cli_provider == "claude":
        return (
            settings.claude_model_complex
            if is_complex_task
            else settings.claude_model_execution
        )

    return "sonnet"


class TestModelSelection:
    """Tests for model selection based on agent type."""

    def test_complex_agents_use_opus_model(self, mock_engine_settings):
        """Business requirement: Quality over speed for planning."""
        mock_engine_settings.cli_provider = "claude"

        for agent in COMPLEX_AGENTS:
            model = get_model_for_agent(agent, settings=mock_engine_settings)
            assert model == "opus", f"{agent} should use Opus"

    def test_execution_agents_use_sonnet_model(self, mock_engine_settings):
        """Business requirement: Speed for implementation."""
        mock_engine_settings.cli_provider = "claude"

        for agent in EXECUTION_AGENTS:
            model = get_model_for_agent(agent, settings=mock_engine_settings)
            assert model == "sonnet", f"{agent} should use Sonnet"

    def test_cursor_complex_agents_use_pro_model(self, mock_engine_settings):
        """Business requirement: Cursor uses appropriate complex model."""
        mock_engine_settings.cli_provider = "cursor"
        mock_engine_settings.cursor_model_complex = "claude-sonnet-4.5"

        for agent in COMPLEX_AGENTS:
            model = get_model_for_agent(agent, settings=mock_engine_settings)
            assert model == "claude-sonnet-4.5", (
                f"{agent} should use Cursor complex model"
            )

    def test_cursor_execution_agents_use_standard_model(self, mock_engine_settings):
        """Business requirement: Cursor uses appropriate execution model."""
        mock_engine_settings.cli_provider = "cursor"
        mock_engine_settings.cursor_model_execution = "composer-1"

        for agent in EXECUTION_AGENTS:
            model = get_model_for_agent(agent, settings=mock_engine_settings)
            assert model == "composer-1", f"{agent} should use Cursor execution model"


class TestProviderSelection:
    """Tests for CLI provider selection."""

    def test_provider_selection_claude(self, mock_engine_settings):
        """Business requirement: Claude provider uses Claude models."""
        mock_engine_settings.cli_provider = "claude"

        model = get_model_for_agent("executor", settings=mock_engine_settings)
        assert model in ["sonnet", "opus"]

    def test_provider_selection_cursor(self, mock_engine_settings):
        """Business requirement: Cursor provider uses Cursor models."""
        mock_engine_settings.cli_provider = "cursor"

        model = get_model_for_agent("executor", settings=mock_engine_settings)
        assert model in ["claude-sonnet-4.5", "composer-1"]

    def test_unknown_provider_uses_default(self, mock_engine_settings):
        """Business requirement: Unknown provider falls back to default."""
        mock_engine_settings.cli_provider = "unknown"

        model = get_model_for_agent("executor", settings=mock_engine_settings)
        assert model == "sonnet"


class TestAgentTypeClassification:
    """Tests for agent type classification."""

    def test_planning_is_complex(self):
        """Planning agent requires high-quality model."""
        assert "planning" in COMPLEX_AGENTS

    def test_brain_is_complex(self):
        """Brain agent requires high-quality model."""
        assert "brain" in COMPLEX_AGENTS

    def test_executor_is_execution(self):
        """Executor agent uses fast model."""
        assert "executor" in EXECUTION_AGENTS

    def test_github_issue_handler_is_execution(self):
        """GitHub issue handler uses fast model."""
        assert "github-issue-handler" in EXECUTION_AGENTS

    def test_case_insensitive_matching(self, mock_engine_settings):
        """Agent type matching is case-insensitive."""
        mock_engine_settings.cli_provider = "claude"

        model1 = get_model_for_agent("PLANNING", settings=mock_engine_settings)
        model2 = get_model_for_agent("planning", settings=mock_engine_settings)
        model3 = get_model_for_agent("Planning", settings=mock_engine_settings)

        assert model1 == model2 == model3 == "opus"


class TestAgentToModelMapping:
    """Tests for complete agent-to-model mapping."""

    def test_agent_type_determines_model(self, mock_engine_settings):
        """Business requirement: Complex tasks get best model."""
        mock_engine_settings.cli_provider = "claude"

        for agent in COMPLEX_AGENTS:
            model = get_model_for_agent(agent, settings=mock_engine_settings)
            assert model in ["opus", "claude-opus-4"], f"{agent} should use Opus"

        for agent in EXECUTION_AGENTS:
            model = get_model_for_agent(agent, settings=mock_engine_settings)
            assert model in ["sonnet", "claude-sonnet-4"], f"{agent} should use Sonnet"
