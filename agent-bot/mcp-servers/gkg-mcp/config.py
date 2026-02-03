from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env")

    gkg_url: str = "http://gkg-service:8003"
    mcp_port: int = 9007
    log_level: str = "INFO"


settings = Settings()
