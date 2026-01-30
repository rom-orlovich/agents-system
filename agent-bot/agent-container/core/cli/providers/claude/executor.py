"""Claude Code CLI executor."""

import asyncio
import json
from typing import Any
import structlog
from ...base import CLIExecutor

logger = structlog.get_logger()


class ClaudeExecutor(CLIExecutor):
    """Execute tasks using Claude Code CLI."""

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute task using Claude CLI."""
        task_id = task.get("task_id", "unknown")
        description = task.get("description", "")
        task_type = task.get("task_type", "execution")

        logger.info("claude_executor_starting", task_id=task_id, task_type=task_type)

        cmd = ["claude", "code", "--prompt", description, "--output", "json"]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            try:
                result = json.loads(stdout.decode())
                logger.info("claude_executor_success", task_id=task_id)
                return {"status": "completed", "result": result}
            except json.JSONDecodeError:
                logger.warning("claude_executor_invalid_json", task_id=task_id)
                return {"status": "completed", "result": {"output": stdout.decode()}}
        else:
            error = stderr.decode()
            logger.error("claude_executor_failed", task_id=task_id, error=error)
            return {"status": "failed", "error": error}

    async def health_check(self) -> bool:
        """Check if Claude CLI is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except FileNotFoundError:
            return False
