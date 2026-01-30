"""Slack API service settings."""

from pydantic import Field, SecretStr, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Slack API service configuration."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", strict=True, frozen=True
    )

    slack_bot_token: SecretStr = Field(description="Slack bot OAuth token")
    redis_url: RedisDsn = Field(description="Redis connection URL")
    rate_limit_per_second: int = Field(default=10, description="Rate limit per second")
    log_level: str = Field(default="INFO", description="Log level")


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
