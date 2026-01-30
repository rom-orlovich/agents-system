from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    github_client_id: str = ""
    github_client_secret: str = ""

    anthropic_api_key: str = ""

    database_url: str = "postgresql://agent:agent@localhost:5432/agent_bot"
    redis_url: str = "redis://localhost:6379"

    log_level: str = "INFO"
    log_format: str = "json"

    repo_base_path: str = "/data/repos"
    repo_max_size_mb: int = 500
    repo_cache_ttl_hours: int = 24

    worker_concurrency: int = 2
    task_timeout_seconds: int = 300

    webhook_secret_rotation_days: int = 90
    token_refresh_margin_hours: int = 1


settings = Settings()
