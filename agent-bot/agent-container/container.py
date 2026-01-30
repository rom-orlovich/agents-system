from dataclasses import dataclass
from typing import Literal, Any

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
    brain_agent: Any | None = None
    conversation_manager: Any | None = None
    analytics: Any | None = None
    result_poster: Any | None = None
    github_mcp: Any | None = None
    jira_mcp: Any | None = None
    slack_mcp: Any | None = None


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

    brain_agent_instance = None
    conversation_manager_instance = None
    analytics_instance = None
    result_poster_instance = None
    github_mcp_instance = None
    jira_mcp_instance = None
    slack_mcp_instance = None

    if config.database_type == "postgres":
        try:
            from core.agents import BrainAgent, ExecutorAgent

            executor = ExecutorAgent(cli_runner)
            brain_agent_instance = BrainAgent(
                planning_agent=None,
                executor_agent=executor,
            )
        except ImportError:
            pass

        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent / "api-gateway"))

            from api.conversations import ConversationManager
            from api.analytics import CostTracker

            if pool:
                conversation_manager_instance = ConversationManager(pool)
                analytics_instance = CostTracker(pool)
        except ImportError:
            pass

        try:
            from core.mcp_client import MCPClient
            from core.mcp_clients import GitHubMCPClient, JiraMCPClient, SlackMCPClient
            from core.result_poster import ResultPoster

            mcp_client = MCPClient()
            github_mcp_instance = GitHubMCPClient(mcp_client)
            jira_mcp_instance = JiraMCPClient(mcp_client)
            slack_mcp_instance = SlackMCPClient(mcp_client)
            result_poster_instance = ResultPoster(mcp_client)
        except ImportError:
            pass

    return Container(
        queue=queue,
        cache=cache,
        cli_runner=cli_runner,
        token_service=token_service,
        brain_agent=brain_agent_instance,
        conversation_manager=conversation_manager_instance,
        analytics=analytics_instance,
        result_poster=result_poster_instance,
        github_mcp=github_mcp_instance,
        jira_mcp=jira_mcp_instance,
        slack_mcp=slack_mcp_instance,
    )
