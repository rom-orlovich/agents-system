from dataclasses import dataclass
from typing import Literal
from ports.queue import QueuePort
from ports.cli_runner import CLIRunnerPort
from adapters.queue.redis_adapter import RedisQueueAdapter
from adapters.queue.memory_adapter import MemoryQueueAdapter


@dataclass
class Config:
    queue_type: Literal["redis", "memory"] = "memory"
    redis_url: str = "redis://localhost:6379"
    cli_type: Literal["claude", "mock"] = "mock"


@dataclass
class Container:
    queue: QueuePort
    cli_runner: CLIRunnerPort


def create_container(config: Config) -> Container:
    if config.queue_type == "redis":
        queue: QueuePort = RedisQueueAdapter(redis_url=config.redis_url)
    else:
        queue = MemoryQueueAdapter()

    from adapters.cli.claude_cli import ClaudeCLIRunner
    from adapters.cli.mock_cli import MockCLIAdapter

    if config.cli_type == "claude":
        cli_runner: CLIRunnerPort = ClaudeCLIRunner()
    else:
        cli_runner = MockCLIAdapter()

    return Container(queue=queue, cli_runner=cli_runner)
