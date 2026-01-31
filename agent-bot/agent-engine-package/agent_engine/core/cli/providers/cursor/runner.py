import asyncio
import json
import os
from pathlib import Path

import structlog

from agent_engine.core.cli.base import CLIResult
from agent_engine.core.cli.providers.cursor.config import CURSOR_CONFIG

logger = structlog.get_logger()


class CursorCLIRunner:
    def __init__(self) -> None:
        self.config = CURSOR_CONFIG

    async def run(
        self,
        prompt: str,
        working_dir: Path,
        output_queue: asyncio.Queue[str | None],
        task_id: str = "",
        timeout_seconds: int = 3600,
        model: str | None = None,
        allowed_tools: str | None = None,
        agents: str | None = None,
        debug_mode: str | None = None,
        mcp_servers: list[str] | None = None,
    ) -> CLIResult:
        cmd = self._build_command(prompt, model, mcp_servers)

        logger.info("starting_cursor_cli", task_id=task_id, working_dir=str(working_dir))

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(working_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                **os.environ,
                "CURSOR_TASK_ID": task_id,
            },
        )

        await output_queue.put(f"[CLI] Cursor process started (PID: {process.pid})\n")

        accumulated_output: list[str] = []
        clean_output: list[str] = []
        cost_usd = 0.0
        input_tokens = 0
        output_tokens = 0
        stderr_lines: list[str] = []

        try:
            async def read_stdout() -> None:
                nonlocal cost_usd, input_tokens, output_tokens

                if not process.stdout:
                    return

                async for line in process.stdout:
                    line_str = line.decode(errors="replace").rstrip("\n\r")

                    if not line_str:
                        continue

                    try:
                        data = json.loads(line_str)
                        self._handle_json_event(
                            data, accumulated_output, clean_output, output_queue
                        )

                        if "cost" in data:
                            cost_usd = data.get("cost", 0.0)
                        if "usage" in data:
                            usage = data["usage"]
                            input_tokens = usage.get("input_tokens", 0)
                            output_tokens = usage.get("output_tokens", 0)

                    except json.JSONDecodeError:
                        accumulated_output.append(line_str + "\n")
                        await output_queue.put(line_str + "\n")

            async def read_stderr() -> None:
                if not process.stderr:
                    return

                async for line in process.stderr:
                    line_str = line.decode().strip()
                    if line_str:
                        stderr_lines.append(line_str)
                        log_line = f"[LOG] {line_str}"
                        accumulated_output.append(log_line + "\n")
                        await output_queue.put(log_line + "\n")

            await asyncio.wait_for(
                asyncio.gather(read_stdout(), read_stderr()), timeout=timeout_seconds
            )
            await process.wait()

            await output_queue.put(None)

            error_msg = self._determine_error_message(
                process.returncode or 0, stderr_lines
            )

            logger.info(
                "cursor_cli_completed",
                task_id=task_id,
                success=process.returncode == 0,
                cost_usd=cost_usd,
            )

            return CLIResult(
                success=process.returncode == 0,
                output="".join(accumulated_output),
                clean_output="".join(clean_output) if clean_output else "",
                cost_usd=cost_usd,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error=error_msg,
            )

        except TimeoutError:
            if process:
                process.kill()
                await process.wait()
            await output_queue.put(None)

            logger.error("cursor_cli_timeout", task_id=task_id, timeout=timeout_seconds)

            return CLIResult(
                success=False,
                output="".join(accumulated_output),
                clean_output="".join(clean_output) if clean_output else "",
                cost_usd=cost_usd,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error=f"Timeout after {timeout_seconds} seconds",
            )

        except Exception as e:
            if process:
                process.kill()
                await process.wait()
            await output_queue.put(None)

            logger.error("cursor_cli_error", task_id=task_id, error=str(e), exc_info=True)

            return CLIResult(
                success=False,
                output="".join(accumulated_output),
                clean_output="".join(clean_output) if clean_output else "",
                cost_usd=cost_usd,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error=f"Unexpected error: {str(e)}",
            )

    def _build_command(
        self,
        prompt: str,
        model: str | None,
        mcp_servers: list[str] | None = None,
    ) -> list[str]:
        cmd = [
            self.config.command,
            self.config.subcommand,
        ]

        if self.config.headless:
            cmd.append("--headless")

        if self.config.print_mode:
            cmd.append("--print")

        cmd.extend(["--output-format", self.config.output_format])

        if model:
            cmd.extend(["--model", model])

        if mcp_servers:
            for server in mcp_servers:
                cmd.extend(["--mcp", server])

        cmd.append(prompt)

        return cmd

    def _handle_json_event(
        self,
        data: dict[str, object],
        accumulated_output: list[str],
        clean_output: list[str],
        output_queue: asyncio.Queue[str | None],
    ) -> None:
        event_type = data.get("type")

        if event_type == "text":
            text = data.get("content", "")
            if text and isinstance(text, str):
                accumulated_output.append(text)
                clean_output.append(text)
                asyncio.create_task(output_queue.put(text))

        elif event_type == "tool_call":
            tool_name = data.get("name", "unknown")
            tool_log = f"\n[TOOL] Using {tool_name}\n"
            accumulated_output.append(tool_log)
            asyncio.create_task(output_queue.put(tool_log))

        elif event_type == "result":
            result_text = data.get("result", "")
            if result_text and isinstance(result_text, str):
                accumulated_output.append(result_text)
                asyncio.create_task(output_queue.put(result_text))

    def _determine_error_message(
        self, returncode: int, stderr_lines: list[str]
    ) -> str | None:
        if returncode == 0:
            return None

        if stderr_lines:
            return "\n".join(stderr_lines) + f"\n\n(Exit code: {returncode})"

        return f"Exit code: {returncode}"
