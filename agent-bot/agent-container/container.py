from dataclasses import dataclass
from typing import Literal

import asyncpg
from pydantic import BaseModel, ConfigDict

from ports import QueuePort, CachePort, CLIRunnerPort
from adapters.memory_queue import InMemoryQueueAdapter
from adapters.memory_cache import InMemoryCacheAdapter
from adapters.queue.redis_adapter import RedisQueueAdapter
from adapters.cli.claude_adapter import ClaudeCLIAdapter
from adapters.database.postgres_installation_repository import (
    PostgresInstallationRepository,
)
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


async def create_container(config: ContainerConfig) -> Container:
    if config.queue_type == "memory":
        queue: QueuePort = InMemoryQueueAdapter()
    elif config.queue_type == "redis":
        queue = RedisQueueAdapter(config.redis_url)
    else:
        raise ValueError(f"Unknown queue type: {config.queue_type}")

    if config.cache_type == "memory":
        cache: CachePort = InMemoryCacheAdapter()
    else:
        raise NotImplementedError("Redis cache not yet implemented")

    if config.database_type == "memory":
        repository = InMemoryInstallationRepository()
    elif config.database_type == "postgres":
        pool = await asyncpg.create_pool(config.database_url)
        if pool is None:
            raise RuntimeError("Failed to create database pool")
        repository = PostgresInstallationRepository(pool)
    else:
        raise ValueError(f"Unknown database type: {config.database_type}")

    token_service = TokenService(repository=repository)

    if config.cli_type == "mock":
        from unittest.mock import AsyncMock
        cli_runner: CLIRunnerPort = AsyncMock()
    elif config.cli_type == "real":
        cli_runner = ClaudeCLIAdapter()
    else:
        raise ValueError(f"Unknown CLI type: {config.cli_type}")

    return Container(
        queue=queue,
        cache=cache,
        cli_runner=cli_runner,
        token_service=token_service,
    )
