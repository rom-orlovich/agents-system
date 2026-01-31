from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 9005
    knowledge_graph_url: str = "http://knowledge-graph:4000"
    request_timeout: float = 30.0

    model_config = {"env_prefix": "KG_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
