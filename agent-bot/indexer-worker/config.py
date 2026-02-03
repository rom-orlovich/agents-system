from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env")

    chromadb_url: str = "http://chromadb:8000"
    gkg_url: str = "http://gkg-service:8003"
    redis_url: str = "redis://redis:6379/0"
    postgres_url: str = "postgresql+asyncpg://agent:agent@postgres:5432/agent_system"
    oauth_service_url: str = "http://oauth-service:8010"

    use_oauth: bool = True
    github_token: str = ""
    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    confluence_url: str = ""
    confluence_email: str = ""
    confluence_api_token: str = ""

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    repos_dir: str = "/data/repos"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8004


settings = Settings()
