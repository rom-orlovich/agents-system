from functools import lru_cache
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env", extra="ignore")

    port: int = 8000
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    github_webhook_secret: str = ""
    jira_webhook_secret: str = ""
    slack_signing_secret: str = ""
    sentry_client_secret: str = ""
    log_level: str = "INFO"
    knowledge_graph_url: str = "http://knowledge-graph:4000"
    agent_engine_url: str = "http://agent-engine:8080"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
