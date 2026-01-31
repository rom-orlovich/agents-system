import asyncio
import os
from enum import Enum
from pathlib import Path
from functools import lru_cache

from cli.base import CLIResult, CLIRunner
from cli.providers.claude import ClaudeCLIRunner
from cli.providers.cursor import CursorCLIRunner


class CLIProviderType(str, Enum):
    CLAUDE = "claude"
    CURSOR = "cursor"


@lru_cache(maxsize=1)
def get_cli_runner() -> CLIRunner:
    provider_type = os.getenv("CLI_PROVIDER", "claude").lower()

    if provider_type == CLIProviderType.CURSOR.value:
        return CursorCLIRunner()

    return ClaudeCLIRunner()


async def run_cli(
    prompt: str,
    working_dir: Path,
    output_queue: asyncio.Queue[str | None],
    task_id: str = "",
    timeout_seconds: int = 3600,
    model: str | None = None,
    allowed_tools: str | None = None,
    agents: str | None = None,
    debug_mode: str | None = None,
) -> CLIResult:
    runner = get_cli_runner()
    return await runner.run(
        prompt=prompt,
        working_dir=working_dir,
        output_queue=output_queue,
        task_id=task_id,
        timeout_seconds=timeout_seconds,
        model=model,
        allowed_tools=allowed_tools,
        agents=agents,
        debug_mode=debug_mode,
    )
