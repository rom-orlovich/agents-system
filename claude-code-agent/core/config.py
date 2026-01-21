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

    @property
    def agents_dir(self) -> Path:
        """Directory containing sub-agents."""
        return self.app_dir / "agents"

    @property
    def skills_dir(self) -> Path:
        """Directory containing brain skills."""
        return self.app_dir / "skills"

    @property
    def credentials_path(self) -> Path:
        """Path to credentials file."""
        return self.data_dir / "credentials" / "claude.json"

    @property
    def registry_dir(self) -> Path:
        """Directory containing registry files."""
        return self.data_dir / "registry"


# Global settings instance
settings = Settings()
