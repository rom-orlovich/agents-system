from functools import lru_cache
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env", extra="ignore")

    port: int = 3003
    slack_bot_token: str
    slack_api_base_url: str = "https://slack.com/api"
    log_level: str = "INFO"
    request_timeout: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
