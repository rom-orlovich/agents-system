"""Test webhook composition pattern - ensure handlers compose utils correctly."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path


class TestGitHubWebhookComposition:
    """Test GitHub webhook handler composition."""

    def test_github_config_loads_at_module_level(self):
        """Test that GitHub config is loaded when routes module is imported."""
        from api.webhooks.github.routes import GITHUB_CONFIG
        assert GITHUB_CONFIG is not None, "GITHUB_CONFIG should be loaded"
        assert hasattr(GITHUB_CONFIG, 'commands'), "Config should have commands"

    def test_github_webhook_handler_initialized(self):
        """Test that webhook_handler is initialized with config."""
        from api.webhooks.github.routes import webhook_handler
        assert webhook_handler is not None, "webhook_handler should be initialized"
        assert webhook_handler.config is not None, "Handler should have config"

    @pytest.mark.asyncio
    async def test_github_handler_verifies_signature(self):
        """Test that handler delegates to utils for signature verification."""
        from api.webhooks.github.handlers import GitHubWebhookHandler

        mock_config = Mock()
        handler = GitHubWebhookHandler(mock_config)

        mock_request = Mock()
        mock_body = b'test body'

        with patch('api.webhooks.github.utils.verify_github_signature', new_callable=AsyncMock) as mock_verify:
            await handler.verify_signature(mock_request, mock_body)
            mock_verify.assert_called_once_with(mock_request, mock_body)

    def test_github_handler_parses_payload(self):
        """Test that handler parses payload correctly."""
        from api.webhooks.github.handlers import GitHubWebhookHandler

        mock_config = Mock()
        handler = GitHubWebhookHandler(mock_config)

        body = b'{"test": "data"}'
        result = handler.parse_payload(body, "github")

        assert result["test"] == "data"
        assert result["provider"] == "github"

    @pytest.mark.asyncio
    async def test_github_handler_validates_webhook(self):
        """Test that handler delegates to validation."""
        from api.webhooks.github.handlers import GitHubWebhookHandler

        mock_config = Mock()
        handler = GitHubWebhookHandler(mock_config)

        mock_payload = {"test": "data"}

        with patch('api.webhooks.github.validation.validate_github_webhook') as mock_validate:
            mock_validate.return_value = Mock(is_valid=True)
            result = await handler.validate_webhook(mock_payload)
            mock_validate.assert_called_once_with(mock_payload)


class TestJiraWebhookComposition:
    """Test Jira webhook handler composition."""

    def test_jira_config_loads_at_module_level(self):
        """Test that Jira config is loaded when routes module is imported."""
        from api.webhooks.jira.routes import JIRA_CONFIG
        assert JIRA_CONFIG is not None, "JIRA_CONFIG should be loaded"
        assert hasattr(JIRA_CONFIG, 'commands'), "Config should have commands"

    def test_jira_webhook_handler_initialized(self):
        """Test that webhook_handler is initialized with config."""
        from api.webhooks.jira.routes import webhook_handler
        assert webhook_handler is not None, "webhook_handler should be initialized"
        assert webhook_handler.config is not None, "Handler should have config"

    @pytest.mark.asyncio
    async def test_jira_handler_verifies_signature(self):
        """Test that handler delegates to utils for signature verification."""
        from api.webhooks.jira.handlers import JiraWebhookHandler

        mock_config = Mock()
        handler = JiraWebhookHandler(mock_config)

        mock_request = Mock()
        mock_body = b'test body'

        with patch('api.webhooks.jira.utils.verify_jira_signature', new_callable=AsyncMock) as mock_verify:
            await handler.verify_signature(mock_request, mock_body)
            mock_verify.assert_called_once_with(mock_request, mock_body)


class TestSlackWebhookComposition:
    """Test Slack webhook handler composition."""

    def test_slack_config_loads_at_module_level(self):
        """Test that Slack config is loaded when routes module is imported."""
        from api.webhooks.slack.routes import SLACK_CONFIG
        assert SLACK_CONFIG is not None, "SLACK_CONFIG should be loaded"
        assert hasattr(SLACK_CONFIG, 'commands'), "Config should have commands"

    def test_slack_webhook_handler_initialized(self):
        """Test that webhook_handler is initialized with config."""
        from api.webhooks.slack.routes import webhook_handler
        assert webhook_handler is not None, "webhook_handler should be initialized"
        assert webhook_handler.config is not None, "Handler should have config"

    @pytest.mark.asyncio
    async def test_slack_handler_verifies_signature(self):
        """Test that handler delegates to utils for signature verification."""
        from api.webhooks.slack.handlers import SlackWebhookHandler

        mock_config = Mock()
        handler = SlackWebhookHandler(mock_config)

        mock_request = Mock()
        mock_body = b'test body'

        with patch('api.webhooks.slack.utils.verify_slack_signature', new_callable=AsyncMock) as mock_verify:
            await handler.verify_signature(mock_request, mock_body)
            mock_verify.assert_called_once_with(mock_request, mock_body)


class TestWebhookConfigLoading:
    """Test webhook config loading from YAML."""

    def test_load_webhook_config_from_yaml_github(self):
        """Test loading GitHub config from YAML."""
        from api.webhooks.common.utils import load_webhook_config_from_yaml

        config_path = Path(__file__).parent.parent.parent / "api" / "webhooks" / "github" / "config.yaml"
        config = load_webhook_config_from_yaml(config_path)

        assert config is not None, "Config should load"
        assert config.name == "github", "Config name should be github"
        assert len(config.commands) > 0, "Should have commands"

    def test_load_webhook_config_from_yaml_jira(self):
        """Test loading Jira config from YAML."""
        from api.webhooks.common.utils import load_webhook_config_from_yaml

        config_path = Path(__file__).parent.parent.parent / "api" / "webhooks" / "jira" / "config.yaml"
        config = load_webhook_config_from_yaml(config_path)

        assert config is not None, "Config should load"
        assert config.name == "jira", "Config name should be jira"
        assert len(config.commands) > 0, "Should have commands"

    def test_load_webhook_config_from_yaml_slack(self):
        """Test loading Slack config from YAML."""
        from api.webhooks.common.utils import load_webhook_config_from_yaml

        config_path = Path(__file__).parent.parent.parent / "api" / "webhooks" / "slack" / "config.yaml"
        config = load_webhook_config_from_yaml(config_path)

        assert config is not None, "Config should load"
        assert config.name == "slack", "Config name should be slack"
        assert len(config.commands) > 0, "Should have commands"

    def test_load_webhook_config_missing_file(self):
        """Test loading config from missing file returns None."""
        from api.webhooks.common.utils import load_webhook_config_from_yaml

        config_path = Path("/nonexistent/config.yaml")
        config = load_webhook_config_from_yaml(config_path)

        assert config is None, "Should return None for missing file"
