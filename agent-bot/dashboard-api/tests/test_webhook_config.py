"""Tests for webhook configuration business logic.

Tests webhook configuration management.
"""

import pytest

from .factories.webhook_factory import (
    WebhookCommand,
    WebhookValidationError,
)


class TestWebhookConfiguration:
    """Tests for webhook configuration."""

    def test_static_webhooks_are_immutable(self, webhook_factory):
        """Business requirement: Cannot modify built-ins."""
        webhook = webhook_factory.create_builtin(provider="github")

        assert webhook.is_builtin is True
        assert webhook.is_mutable() is False

    def test_dynamic_webhook_is_mutable(self, webhook_factory):
        """Business requirement: User webhooks work."""
        webhook = webhook_factory.create_dynamic()

        assert webhook.is_builtin is False
        assert webhook.is_mutable() is True


class TestWebhookEndpointValidation:
    """Tests for webhook endpoint format."""

    def test_webhook_endpoint_format_validated(self, webhook_factory):
        """Business requirement: URL safety."""
        valid_webhook = webhook_factory.create(endpoint="/webhooks/my-hook")
        valid_webhook.validate()

        invalid_webhook = webhook_factory.create(endpoint="/invalid/path")
        with pytest.raises(WebhookValidationError):
            invalid_webhook.validate()

    def test_endpoint_allows_lowercase_alphanumeric(self, webhook_factory):
        """Endpoint allows lowercase letters, numbers, hyphens."""
        valid_endpoints = [
            "/webhooks/github",
            "/webhooks/my-webhook-123",
            "/webhooks/test-hook",
        ]

        for endpoint in valid_endpoints:
            webhook = webhook_factory.create(endpoint=endpoint)
            webhook.validate()

    def test_endpoint_rejects_invalid_patterns(self, webhook_factory):
        """Endpoint rejects invalid patterns."""
        invalid_endpoints = [
            "/webhooks/My-Hook",
            "/webhooks/hook_underscore",
            "/api/webhooks/hook",
            "webhooks/no-slash",
        ]

        for endpoint in invalid_endpoints:
            webhook = webhook_factory.create(endpoint=endpoint)
            with pytest.raises(WebhookValidationError):
                webhook.validate()


class TestWebhookCommands:
    """Tests for webhook command configuration."""

    def test_webhook_requires_commands(self, webhook_factory):
        """Business requirement: Must have actions."""
        webhook = webhook_factory.create(commands=[])

        with pytest.raises(WebhookValidationError):
            webhook.validate()

    def test_no_duplicate_command_names(self, webhook_factory):
        """Business requirement: Command uniqueness."""
        commands = [
            WebhookCommand(name="process", trigger="*", action="task", template="t"),
            WebhookCommand(name="process", trigger="*", action="task", template="t"),
        ]
        webhook = webhook_factory.create(commands=commands)

        with pytest.raises(WebhookValidationError):
            webhook.validate()

    def test_default_command_must_exist(self, webhook_factory):
        """Business requirement: Valid default."""
        commands = [
            WebhookCommand(name="handle", trigger="*", action="task", template="t"),
        ]
        webhook = webhook_factory.create(
            commands=commands,
            default_command="nonexistent",
        )

        with pytest.raises(WebhookValidationError):
            webhook.validate()

    def test_command_requires_template(self, webhook_factory):
        """Business requirement: Action definition."""
        commands = [
            WebhookCommand(name="process", trigger="*", action="task", template=""),
        ]
        webhook = webhook_factory.create(commands=commands)

        with pytest.raises(WebhookValidationError):
            webhook.validate()


class TestBuiltinWebhooks:
    """Tests for built-in webhook configurations."""

    def test_github_webhook_configuration(self, webhook_factory):
        """GitHub webhook has correct structure."""
        webhook = webhook_factory.create_github_webhook()

        assert webhook.provider == "github"
        assert webhook.endpoint == "/webhooks/github"
        assert webhook.is_builtin is True
        assert len(webhook.commands) >= 2
        webhook.validate()

    def test_jira_webhook_configuration(self, webhook_factory):
        """Jira webhook has correct structure."""
        webhook = webhook_factory.create_jira_webhook()

        assert webhook.provider == "jira"
        assert webhook.endpoint == "/webhooks/jira"
        assert webhook.is_builtin is True
        webhook.validate()

    def test_builtin_webhook_has_all_required_fields(self, webhook_factory):
        """Built-in webhooks have complete configuration."""
        github = webhook_factory.create_github_webhook()
        jira = webhook_factory.create_jira_webhook()

        for webhook in [github, jira]:
            assert webhook.name
            assert webhook.provider
            assert webhook.endpoint
            assert len(webhook.commands) > 0
            assert webhook.default_command in [c.name for c in webhook.commands]


class TestWebhookValidation:
    """Tests for complete webhook validation."""

    def test_valid_webhook_passes_validation(self, webhook_factory):
        """Valid webhook configuration passes."""
        webhook = webhook_factory.create(
            endpoint="/webhooks/valid-hook",
            commands=[
                WebhookCommand(
                    name="process",
                    trigger="event",
                    action="create_task",
                    template="Process: {{ data }}",
                )
            ],
            default_command="process",
        )

        webhook.validate()

    def test_multiple_validation_errors(self, webhook_factory):
        """Validation catches first error."""
        webhook = webhook_factory.create(
            endpoint="/invalid",
            commands=[],
        )

        with pytest.raises(WebhookValidationError):
            webhook.validate()
