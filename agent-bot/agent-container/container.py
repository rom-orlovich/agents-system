from dataclasses import dataclass
from ports import QueuePort, CLIRunnerPort
from adapters.queue.redis_adapter import RedisQueueAdapter
from adapters.queue.memory_adapter import MemoryQueueAdapter
from core.cli_runner.claude_cli_runner import ClaudeCLIRunner
from typing import Literal


@dataclass
class Config:
    queue_type: Literal["redis", "memory"] = "redis"
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "tasks"
    cli_type: Literal["claude", "mock"] = "claude"


@dataclass
class Container:
    queue: QueuePort
    cli_runner: CLIRunnerPort


def create_container(config: Config) -> Container:
    if config.queue_type == "redis":
        queue: QueuePort = RedisQueueAdapter(
            redis_url=config.redis_url,
            queue_name=config.queue_name,
        )
    else:
        queue = MemoryQueueAdapter()

    if config.cli_type == "claude":
        cli_runner: CLIRunnerPort = ClaudeCLIRunner()
    else:
        from adapters.cli.mock_adapter import MockCLIAdapter

        cli_runner = MockCLIAdapter()

    return Container(
        queue=queue,
        cli_runner=cli_runner,
    )
