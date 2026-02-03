from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env")

    chromadb_url: str = "http://chromadb:8000"
    gkg_url: str = "http://gkg-service:8003"
    redis_url: str = "redis://redis:6379/0"
    postgres_url: str = "postgresql+asyncpg://agent:agent@postgres:5432/agent_system"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    default_top_k: int = 10
    rerank_threshold: int = 20
    cache_ttl_seconds: int = 300

    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8002


settings = Settings()
