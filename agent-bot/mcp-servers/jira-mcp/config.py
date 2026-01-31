from functools import lru_cache
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env", extra="ignore")

    port: int = 9002
    jira_api_url: str = "http://jira-api:3002"
    request_timeout: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
