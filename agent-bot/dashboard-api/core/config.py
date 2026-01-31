from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    redis_url: str = "redis://redis:6379/0"
    database_url: str = "postgresql+asyncpg://agent:agent@postgres:5432/agent_system"
    agent_engine_url: str = "http://agent-engine:8080"

    port: int = 5000
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3005,http://external-dashboard:3005"
