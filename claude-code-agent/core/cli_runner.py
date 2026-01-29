import asyncio
from pathlib import Path
from typing import Optional

from core.cli.base import CLIResult
from core.cli.claude import ClaudeCLIRunner

_default_cli_runner = ClaudeCLIRunner()


async def run_claude_cli(
    prompt: str,
    working_dir: Path,
    output_queue: asyncio.Queue,
    task_id: str = "",
    timeout_seconds: int = 3600,
    model: Optional[str] = None,
    allowed_tools: Optional[str] = None,
    agents: Optional[str] = None,
    debug_mode: Optional[str] = None,
) -> CLIResult:
    return await _default_cli_runner.run(
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
