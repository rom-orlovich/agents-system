"""Application configuration."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Machine Identity
    machine_id: str = "claude-agent-001"

    # Task Management
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 3600

    # Paths
    data_dir: Path = Path("/data")
    app_dir: Path = Path("/app")

    # Database
    redis_url: str = "redis://redis:6379/0"
    database_url: str = "sqlite+aiosqlite:////data/db/machine.db"

    # Logging
    log_level: str = "INFO"
    log_json: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS
    cors_origins: list[str] = ["*"]

    # Webhook Security
    github_webhook_secret: str | None = None
    jira_webhook_secret: str | None = None

    # Storage Backend (for cloud deployment)
    storage_backend: str = "local"  # "local", "s3", or "postgresql"
    s3_bucket: str | None = None
    s3_prefix: str = "claude-agent"

    # Claude CLI Configuration
    default_model: str | None = None  # e.g., "opus", "sonnet" (None = CLI default)
    default_allowed_tools: str = "Read,Edit,Bash,Glob,Grep,Write"  # Pre-approved tools
    enable_subagents: bool = True  # Enable sub-agent execution

    @property
    def agents_dir(self) -> Path:
        """Directory containing BUILT-IN sub-agents (read-only from image)."""
        return self.app_dir / "agents"

    @property
    def user_agents_dir(self) -> Path:
        """Directory for USER-UPLOADED agents (persisted in /data volume)."""
        return self.data_dir / "config" / "agents"

    @property
    def skills_dir(self) -> Path:
        """Directory containing BUILT-IN brain skills (read-only from image)."""
        return self.app_dir / "skills"

    @property
    def user_skills_dir(self) -> Path:
        """Directory for USER-UPLOADED skills (persisted in /data volume)."""
        return self.data_dir / "config" / "skills"

    @property
    def credentials_path(self) -> Path:
        """Path to credentials file (persisted in /data volume)."""
        return self.data_dir / "credentials" / "claude.json"

    @property
    def registry_dir(self) -> Path:
        """Directory containing registry files (persisted in /data volume)."""
        return self.data_dir / "registry"


# Global settings instance
settings = Settings()
