from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379/0"
    logs_dir: Path = Path("/data/logs/tasks")
    redis_stream: str = "task_events"
    redis_consumer_group: str = "task-logger"
    max_batch_size: int = 10
    port: int = 8090
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
