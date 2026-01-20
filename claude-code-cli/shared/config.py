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
    DATABASE_URL: str = "postgresql://aiagent:localdev@localhost:5432/aiagent"



    # Queue Names
    PLANNING_QUEUE: str = "planning_queue"
    EXECUTION_QUEUE: str = "execution_queue"

    # GitHub
    GITHUB_TOKEN: Optional[str] = None
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
    SLACK_WORKSPACE_DOMAIN: Optional[str] = None
    SLACK_CHANNEL_AGENTS: str = "#ai-agents"
    SLACK_CHANNEL_ERRORS: str = "#ai-errors"

    # Claude
    CLAUDE_CONFIG_DIR: str = os.path.expanduser("~/.claude")
    
    # Claude Model Selection
    # Planning/Discovery uses Opus 4.5 for better reasoning and analysis
    CLAUDE_PLANNING_MODEL: str = "claude-opus-4-5-20251101"
    # Coding/Execution uses Sonnet 4.5 for faster, cost-effective implementation
    CLAUDE_CODING_MODEL: str = "claude-sonnet-4-5-20250929"

    # Agent Configuration
    PLANNING_AGENT_TIMEOUT: int = 300  # 5 minutes
    EXECUTOR_AGENT_TIMEOUT: int = 600  # 10 minutes
    MAX_BUDGET_USD: float = 1000.0  # Effectiveness disabled as per user request

    # Workspace
    WORKSPACE_PATH: str = "/workspace"

    # Dashboard
    DASHBOARD_URL: str = "http://localhost:8080"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000


# Global settings instance
settings = Settings()
