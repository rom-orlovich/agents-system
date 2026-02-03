from functools import lru_cache
from typing import Literal
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env", extra="ignore")

    port: int = 8080
    cli_provider: Literal["claude", "cursor"] = "claude"
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "agent"
    postgres_password: str = "agent"
    postgres_db: str = "agent_system"
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 3600
    log_level: str = "INFO"
    internal_dashboard_api_url: str = "http://internal-dashboard-api:5000"

    knowledge_services_enabled: bool = False
    knowledge_graph_url: str = "http://gkg-service:4000"
    llamaindex_url: str = "http://llamaindex-service:8100"
    knowledge_timeout_seconds: float = 10.0
    knowledge_retry_count: int = 2

    claude_model_complex: str = "opus"
    claude_model_execution: str = "sonnet"
    cursor_model_complex: str = "claude-sonnet-4.5"
    cursor_model_execution: str = "composer-1"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def postgres_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
