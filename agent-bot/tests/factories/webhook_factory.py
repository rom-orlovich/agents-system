"""Webhook configuration factory for testing."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import re


ENDPOINT_PATTERN = re.compile(r"^/webhooks/[a-z0-9-]+$")


class WebhookValidationError(Exception):
    """Raised when webhook configuration validation fails."""

    pass


@dataclass
class WebhookCommand:
    """Webhook command configuration."""

    name: str
    trigger: str
    action: str
    template: str
    agent: str | None = None
    conditions: dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass
class WebhookConfig:
    """Webhook configuration for testing."""

    webhook_id: str
    name: str
    provider: str
    endpoint: str
    commands: list[WebhookCommand] = field(default_factory=list)
    secret: str | None = None
    enabled: bool = True
    is_builtin: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    default_command: str | None = None

    def validate(self) -> None:
        """Validate webhook configuration."""
        if not ENDPOINT_PATTERN.match(self.endpoint):
            raise WebhookValidationError(
                f"Endpoint must match pattern: /webhooks/[a-z0-9-]+, got: {self.endpoint}"
            )

        if not self.commands:
            raise WebhookValidationError("Commands list cannot be empty")

        command_names = [cmd.name for cmd in self.commands]
        if len(command_names) != len(set(command_names)):
            raise WebhookValidationError("Duplicate command names not allowed")

        if self.default_command and self.default_command not in command_names:
            raise WebhookValidationError(
                f"Default command '{self.default_command}' not found in commands"
            )

        for cmd in self.commands:
            if not cmd.template:
                raise WebhookValidationError(
                    f"Command '{cmd.name}' must have a template"
                )

    def is_mutable(self) -> bool:
        """Check if webhook can be modified."""
        return not self.is_builtin


class WebhookFactory:
    """Factory for creating test webhook configurations."""

    _counter: int = 0

    @classmethod
    def create(
        cls,
        webhook_id: str | None = None,
        name: str = "Test Webhook",
        provider: str = "github",
        endpoint: str | None = None,
        commands: list[WebhookCommand] | None = None,
        **kwargs,
    ) -> WebhookConfig:
        """Create a test webhook configuration."""
        cls._counter += 1
        if webhook_id is None:
            webhook_id = f"webhook-{cls._counter:03d}"
        if endpoint is None:
            endpoint = f"/webhooks/test-{cls._counter:03d}"
        if commands is None:
            commands = [
                WebhookCommand(
                    name="default",
                    trigger="*",
                    action="create_task",
                    template="Process event: {{ event }}",
                )
            ]

        return WebhookConfig(
            webhook_id=webhook_id,
            name=name,
            provider=provider,
            endpoint=endpoint,
            commands=commands,
            **kwargs,
        )

    @classmethod
    def create_github_webhook(cls, **kwargs) -> WebhookConfig:
        """Create a GitHub webhook configuration."""
        commands = [
            WebhookCommand(
                name="issue_opened",
                trigger="issues.opened",
                action="create_task",
                template="Handle GitHub issue: {{ issue.title }}",
                agent="github-issue-handler",
            ),
            WebhookCommand(
                name="pr_opened",
                trigger="pull_request.opened",
                action="create_task",
                template="Review PR: {{ pull_request.title }}",
                agent="github-pr-review",
            ),
        ]
        return cls.create(
            name="GitHub Webhook",
            provider="github",
            endpoint="/webhooks/github",
            commands=commands,
            default_command="issue_opened",
            is_builtin=True,
            **kwargs,
        )

    @classmethod
    def create_jira_webhook(cls, **kwargs) -> WebhookConfig:
        """Create a Jira webhook configuration."""
        commands = [
            WebhookCommand(
                name="issue_created",
                trigger="jira:issue_created",
                action="create_task",
                template="Handle Jira issue: {{ issue.key }}",
                agent="jira-code-plan",
                conditions={"labels": ["AI-Fix"]},
            ),
        ]
        return cls.create(
            name="Jira Webhook",
            provider="jira",
            endpoint="/webhooks/jira",
            commands=commands,
            default_command="issue_created",
            is_builtin=True,
            **kwargs,
        )

    @classmethod
    def create_builtin(cls, provider: str = "github", **kwargs) -> WebhookConfig:
        """Create a builtin (immutable) webhook."""
        return cls.create(provider=provider, is_builtin=True, **kwargs)

    @classmethod
    def create_dynamic(cls, **kwargs) -> WebhookConfig:
        """Create a dynamic (mutable) webhook."""
        return cls.create(is_builtin=False, **kwargs)

    @classmethod
    def reset(cls) -> None:
        """Reset the factory counter."""
        cls._counter = 0
