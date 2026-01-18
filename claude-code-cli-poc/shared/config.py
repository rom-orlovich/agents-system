"""
Centralized Configuration Settings
==================================
All settings loaded from environment variables with Pydantic validation.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class JiraSettings(BaseSettings):
    """Jira Configuration."""

    base_url: str = Field(default="", alias="JIRA_BASE_URL")
    email: str = Field(default="", alias="JIRA_EMAIL")
    api_token: str = Field(default="", alias="JIRA_API_TOKEN")
    project_key: str = Field(default="PROJ", alias="JIRA_PROJECT_KEY")
    ai_label: str = Field(default="AI-Fix", alias="JIRA_AI_LABEL")
    webhook_secret: str = Field(default="", alias="JIRA_WEBHOOK_SECRET")


class GitHubSettings(BaseSettings):
    """GitHub Configuration."""

    token: str = Field(default="", alias="GITHUB_TOKEN")
    org: str = Field(default="", alias="GITHUB_ORG")
    webhook_secret: str = Field(default="", alias="GITHUB_WEBHOOK_SECRET")


class SentrySettings(BaseSettings):
    """Sentry Configuration."""

    org: str = Field(default="", alias="SENTRY_ORG")
    auth_token: str = Field(default="", alias="SENTRY_AUTH_TOKEN")
    webhook_secret: str = Field(default="", alias="SENTRY_WEBHOOK_SECRET")


class RedisSettings(BaseSettings):
    """Redis Configuration."""

    url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")


class AgentSettings(BaseSettings):
    """Agent Configuration."""

    workspace_dir: str = Field(default="/workspace/repos", alias="WORKSPACE_DIR")
    task_timeout_minutes: int = Field(default=30, alias="TASK_TIMEOUT_MINUTES")
    max_fix_attempts: int = Field(default=3, alias="MAX_FIX_ATTEMPTS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    claude_config_dir: str = Field(default="/root/.claude", alias="CLAUDE_CONFIG_DIR")


class WebhookSettings(BaseSettings):
    """Webhook Server Configuration."""

    host: str = Field(default="0.0.0.0", alias="WEBHOOK_HOST")
    port: int = Field(default=8000, alias="WEBHOOK_PORT")
    approval_patterns: str = Field(
        default="@agent approve,/approve,LGTM", alias="APPROVAL_PATTERNS"
    )

    @property
    def approval_pattern_list(self) -> List[str]:
        """Get approval patterns as a list."""
        return [p.strip().lower() for p in self.approval_patterns.split(",")]


class SlackSettings(BaseSettings):
    """Slack Configuration."""

    bot_token: str = Field(default="", alias="SLACK_BOT_TOKEN")
    channel_agents: str = Field(default="#ai-agents", alias="SLACK_CHANNEL_AGENTS")
    channel_errors: str = Field(default="#ai-errors", alias="SLACK_CHANNEL_ERRORS")


class Settings(BaseSettings):
    """Main Settings Container."""

    jira: JiraSettings = Field(default_factory=JiraSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    sentry: SentrySettings = Field(default_factory=SentrySettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)
    slack: SlackSettings = Field(default_factory=SlackSettings)

    def validate_required(self) -> List[str]:
        """Validate required settings are present."""
        errors = []
        if not self.github.token:
            errors.append("GITHUB_TOKEN is required")
        if not self.github.org:
            errors.append("GITHUB_ORG is required")
        return errors


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get singleton Settings instance."""
    return Settings()
