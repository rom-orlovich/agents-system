"""Configuration management using Pydantic settings."""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 10

    # PostgreSQL
    DATABASE_URL: str = "postgresql://aiagent:localdev@localhost:5432/aiagent"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Queue Names
    PLANNING_QUEUE: str = "planning_queue"
    EXECUTION_QUEUE: str = "execution_queue"

    # GitHub
    GITHUB_TOKEN: str
    GITHUB_ORG: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: Optional[str] = None

    # Jira
    JIRA_URL: Optional[str] = None
    JIRA_EMAIL: Optional[str] = None
    JIRA_API_TOKEN: Optional[str] = None
    JIRA_PROJECT: Optional[str] = None

    # Sentry
    SENTRY_AUTH_TOKEN: Optional[str] = None
    SENTRY_ORG: Optional[str] = None
    SENTRY_HOST: str = "sentry.io"

    # Slack
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None
    SLACK_CHANNEL_AGENTS: str = "#ai-agents"
    SLACK_CHANNEL_ERRORS: str = "#ai-errors"

    # Claude
    CLAUDE_CONFIG_DIR: str = os.path.expanduser("~/.claude")

    # Agent Configuration
    PLANNING_AGENT_TIMEOUT: int = 300  # 5 minutes
    EXECUTOR_AGENT_TIMEOUT: int = 600  # 10 minutes

    # Workspace
    WORKSPACE_PATH: str = "/workspace"

    # Dashboard
    DASHBOARD_URL: str = "http://localhost:3000"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000


# Global settings instance
settings = Settings()
