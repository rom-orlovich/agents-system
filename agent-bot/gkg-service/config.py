from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(strict=True, env_file=".env")

    data_dir: str = "/data/gkg"
    repos_dir: str = "/data/repos"
    gkg_binary: str = "/usr/local/bin/gkg"

    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8003


settings = Settings()
