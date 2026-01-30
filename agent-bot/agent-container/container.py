from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ports import QueuePort, CachePort, CLIRunnerPort
from adapters.memory_queue import InMemoryQueueAdapter
from adapters.memory_cache import InMemoryCacheAdapter
from token_service import TokenService, InMemoryInstallationRepository


class ContainerConfig(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    queue_type: Literal["memory", "redis"]
    cache_type: Literal["memory", "redis"] = "memory"
    database_type: Literal["memory", "postgres"]
    cli_type: Literal["real", "mock"]
    redis_url: str = ""
    database_url: str = ""


@dataclass
class Container:
    queue: QueuePort
    cache: CachePort
    cli_runner: CLIRunnerPort
    token_service: TokenService


def create_container(config: ContainerConfig) -> Container:
    if config.queue_type == "memory":
        queue: QueuePort = InMemoryQueueAdapter()
    else:
        raise NotImplementedError("Redis queue not yet implemented")

    if config.cache_type == "memory":
        cache: CachePort = InMemoryCacheAdapter()
    else:
        raise NotImplementedError("Redis cache not yet implemented")

    if config.database_type == "memory":
        repository = InMemoryInstallationRepository()
    else:
        raise NotImplementedError("Postgres repository not yet implemented")

    token_service = TokenService(repository=repository)

    if config.cli_type == "mock":
        from unittest.mock import AsyncMock
        cli_runner: CLIRunnerPort = AsyncMock()
    else:
        raise NotImplementedError("Real CLI runner not yet implemented")

    return Container(
        queue=queue,
        cache=cache,
        cli_runner=cli_runner,
        token_service=token_service,
    )
