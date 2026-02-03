from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env")

    llamaindex_url: str = "http://llamaindex-service:8002"
    mcp_port: int = 9006
    log_level: str = "INFO"
    redis_url: str = "redis://redis:6379/0"
    publish_knowledge_events: bool = True


settings = Settings()
