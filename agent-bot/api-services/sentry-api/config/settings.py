from functools import lru_cache
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env", extra="ignore")

    port: int = 3004
    sentry_auth_token: str
    sentry_org_slug: str
    sentry_api_base_url: str = "https://sentry.io/api/0"
    log_level: str = "INFO"
    request_timeout: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
