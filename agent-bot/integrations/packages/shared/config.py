"""Centralized configuration management using Pydantic."""

from typing import Literal
from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database connection configuration."""

    model_config = SettingsConfigDict(strict=True, frozen=True)

    postgres_url: PostgresDsn = Field(description="PostgreSQL connection URL")
    redis_url: RedisDsn = Field(description="Redis connection URL")


class CLIConfig(BaseSettings):
    """CLI provider configuration."""

    model_config = SettingsConfigDict(strict=True, frozen=True)

    cli_provider: Literal["claude-code-cli", "cursor-cli"] = Field(
        default="claude-code-cli", description="CLI tool to use for agent execution"
    )


class ExternalAPIConfig(BaseSettings):
    """External API credentials."""

    model_config = SettingsConfigDict(strict=True, frozen=True)

    github_token: SecretStr = Field(description="GitHub personal access token")
    jira_api_key: SecretStr = Field(description="Jira API key")
    jira_url: HttpUrl = Field(description="Jira instance URL")
    jira_email: str = Field(description="Jira account email")
    slack_bot_token: SecretStr = Field(description="Slack bot OAuth token")
    sentry_auth_token: SecretStr = Field(description="Sentry auth token")


class ServiceURLConfig(BaseSettings):
    """Internal service URLs."""

    model_config = SettingsConfigDict(strict=True, frozen=True)

    github_api_url: HttpUrl = Field(default="http://github-api:3001")
    jira_api_url: HttpUrl = Field(default="http://jira-api:3002")
    slack_api_url: HttpUrl = Field(default="http://slack-api:3003")
    sentry_api_url: HttpUrl = Field(default="http://sentry-api:3004")
    knowledge_graph_url: HttpUrl = Field(default="http://knowledge-graph:4000")


class MonitoringConfig(BaseSettings):
    """Monitoring and observability settings."""

    model_config = SettingsConfigDict(strict=True, frozen=True)

    prometheus_metrics_enabled: bool = Field(default=True)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )


class Settings(BaseSettings):
    """Application settings aggregator."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", strict=True, frozen=True
    )

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cli: CLIConfig = Field(default_factory=CLIConfig)
    external_apis: ExternalAPIConfig = Field(default_factory=ExternalAPIConfig)
    service_urls: ServiceURLConfig = Field(default_factory=ServiceURLConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
