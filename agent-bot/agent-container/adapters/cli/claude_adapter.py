import asyncio
import re
import time
from pathlib import Path

import structlog

from ports.cli_runner import CLIExecutionResult

logger = structlog.get_logger()

TOKEN_PATTERN = re.compile(r"(?:used\s+)?(\d+)\s+tokens?(?:\s+used)?", re.IGNORECASE)
COST_PATTERN = re.compile(r"\$?([\d.]+)\s+(?:USD|cost)", re.IGNORECASE)


class ClaudeCLIAdapter:
    def __init__(self, claude_binary: str = "claude") -> None:
        self._claude_binary = claude_binary

    async def execute_and_wait(
        self,
        command: list[str],
        input_text: str,
        timeout_seconds: int,
    ) -> CLIExecutionResult:
        start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(input_text.encode()),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                duration = time.time() - start_time

                logger.warning(
                    "cli_execution_timeout",
                    command=command,
                    timeout_seconds=timeout_seconds,
                )

                return CLIExecutionResult(
                    success=False,
                    output="",
                    error=f"Execution timed out after {timeout_seconds}s",
                    exit_code=-1,
                    duration_seconds=duration,
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            duration = time.time() - start_time

            exit_code = process.returncode if process.returncode is not None else -1
            success = exit_code == 0

            tokens_used = self._extract_tokens(stdout + stderr)
            cost_usd = self._extract_cost(stdout + stderr)

            logger.info(
                "cli_execution_completed",
                command=command,
                exit_code=exit_code,
                success=success,
                duration=duration,
                tokens=tokens_used,
                cost=cost_usd,
            )

            return CLIExecutionResult(
                success=success,
                output=stdout,
                error=stderr if stderr else None,
                exit_code=exit_code,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                duration_seconds=duration,
            )

        except FileNotFoundError:
            logger.error("claude_binary_not_found", binary=command[0])
            return CLIExecutionResult(
                success=False,
                output="",
                error=f"Claude binary not found: {command[0]}",
                exit_code=-1,
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            logger.error(
                "cli_execution_failed",
                command=command,
                error=str(e),
            )
            return CLIExecutionResult(
                success=False,
                output="",
                error=f"Execution failed: {str(e)}",
                exit_code=-1,
                duration_seconds=time.time() - start_time,
            )

    async def execute_streaming(
        self,
        command: list[str],
        input_text: str,
    ):
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if process.stdin:
            process.stdin.write(input_text.encode())
            await process.stdin.drain()
            process.stdin.close()

        if process.stdout:
            async for line in process.stdout:
                yield line.decode("utf-8", errors="replace")

        await process.wait()

    def _extract_tokens(self, text: str) -> int:
        match = TOKEN_PATTERN.search(text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return 0

    def _extract_cost(self, text: str) -> float:
        match = COST_PATTERN.search(text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return 0.0
