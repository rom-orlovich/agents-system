import asyncio
import json
import os
from pathlib import Path
import structlog

from agent_engine.core.cli.base import CLIResult
from agent_engine.core.cli.sanitization import sanitize_sensitive_content, contains_sensitive_data
from agent_engine.core.cli.providers.claude.config import CLAUDE_CONFIG

logger = structlog.get_logger()


class ClaudeCLIRunner:
    def __init__(self) -> None:
        self.config = CLAUDE_CONFIG

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
    ) -> CLIResult:
        cmd = self._build_command(prompt, model, allowed_tools, agents, debug_mode)

        logger.info("starting_claude_cli", task_id=task_id, working_dir=str(working_dir))

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(working_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                **os.environ,
                "CLAUDE_TASK_ID": task_id,
                "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
            },
        )

        await output_queue.put(f"[CLI] Process started (PID: {process.pid})\n")

        accumulated_output: list[str] = []
        clean_output: list[str] = []
        cost_usd = 0.0
        input_tokens = 0
        output_tokens = 0
        cli_error_message: str | None = None
        has_streaming_output = False

        try:
            result = await self._process_streams(
                process=process,
                output_queue=output_queue,
                task_id=task_id,
                timeout_seconds=timeout_seconds,
                accumulated_output=accumulated_output,
                clean_output=clean_output,
            )

            cost_usd = result["cost_usd"]
            input_tokens = result["input_tokens"]
            output_tokens = result["output_tokens"]
            cli_error_message = result["cli_error_message"]
            has_streaming_output = result["has_streaming_output"]

            await output_queue.put(None)

            error_msg = self._determine_error_message(
                process.returncode or 0, cli_error_message, result.get("stderr_lines", [])
            )

            logger.info(
                "claude_cli_completed",
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

        except asyncio.TimeoutError:
            if process:
                process.kill()
                await process.wait()
            await output_queue.put(None)

            logger.error("cli_timeout", task_id=task_id, timeout=timeout_seconds)

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

            logger.error("cli_error", task_id=task_id, error=str(e), exc_info=True)

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
        allowed_tools: str | None,
        agents: str | None,
        debug_mode: str | None,
    ) -> list[str]:
        cmd = [
            self.config.command,
            "-p",
            "--output-format",
            self.config.output_format,
            "--verbose",
            "--dangerously-skip-permissions",
            "--include-partial-messages",
        ]

        if debug_mode is not None:
            if debug_mode:
                cmd.extend(["--debug", debug_mode])
            else:
                cmd.append("--debug")

        if model:
            cmd.extend(["--model", model])

        if allowed_tools:
            cmd.extend(["--allowedTools", allowed_tools])

        if agents:
            cmd.extend(["--agents", agents])

        cmd.extend(["--", prompt])

        return cmd

    async def _process_streams(
        self,
        process: asyncio.subprocess.Process,
        output_queue: asyncio.Queue[str | None],
        task_id: str,
        timeout_seconds: int,
        accumulated_output: list[str],
        clean_output: list[str],
    ) -> dict[str, float | int | str | list[str] | bool | None]:
        cost_usd = 0.0
        input_tokens = 0
        output_tokens = 0
        cli_error_message: str | None = None
        has_streaming_output = False
        stderr_lines: list[str] = []

        async def read_stdout() -> None:
            nonlocal cost_usd, input_tokens, output_tokens, cli_error_message, has_streaming_output

            if not process.stdout:
                return

            async for line in process.stdout:
                line_str = line.decode(errors="replace").rstrip("\n\r")

                if not line_str:
                    continue

                result = self._parse_json_line(
                    line_str, task_id, accumulated_output, clean_output, output_queue
                )

                if result:
                    if "cost_usd" in result:
                        cost_usd = result["cost_usd"]
                    if "input_tokens" in result:
                        input_tokens = result["input_tokens"]
                    if "output_tokens" in result:
                        output_tokens = result["output_tokens"]
                    if "cli_error_message" in result:
                        cli_error_message = result["cli_error_message"]
                    if result.get("has_streaming_output"):
                        has_streaming_output = True

        async def read_stderr() -> None:
            if not process.stderr:
                return

            async for line in process.stderr:
                line_str = line.decode().strip()
                if not line_str:
                    continue

                stderr_lines.append(line_str)
                log_line = f"[LOG] {line_str}"
                accumulated_output.append(log_line + "\n")
                await output_queue.put(log_line + "\n")

        await asyncio.wait_for(
            asyncio.gather(read_stdout(), read_stderr()), timeout=timeout_seconds
        )
        await process.wait()

        return {
            "cost_usd": cost_usd,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cli_error_message": cli_error_message,
            "has_streaming_output": has_streaming_output,
            "stderr_lines": stderr_lines,
        }

    def _parse_json_line(
        self,
        line_str: str,
        task_id: str,
        accumulated_output: list[str],
        clean_output: list[str],
        output_queue: asyncio.Queue[str | None],
    ) -> dict[str, float | int | str | bool | None] | None:
        try:
            data = json.loads(line_str)
        except json.JSONDecodeError:
            accumulated_output.append(line_str + "\n")
            asyncio.create_task(output_queue.put(line_str + "\n"))
            return None

        msg_type = data.get("type")
        result: dict[str, float | int | str | bool | None] = {}

        if msg_type == "init":
            init_content = data.get("content", "")
            if init_content:
                accumulated_output.append(init_content)
                asyncio.create_task(output_queue.put(init_content))

        elif msg_type == "assistant":
            self._handle_assistant_message(data, task_id, accumulated_output, clean_output, output_queue, result)

        elif msg_type == "stream_event":
            event = data.get("event", {})
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        result["has_streaming_output"] = True
                        accumulated_output.append(text)
                        clean_output.append(text)
                        asyncio.create_task(output_queue.put(text))

        elif msg_type == "result":
            result["cost_usd"] = data.get("total_cost_usd", data.get("cost_usd", 0.0))
            usage = data.get("usage", {})
            result["input_tokens"] = usage.get("input_tokens", 0)
            result["output_tokens"] = usage.get("output_tokens", 0)

            result_text = data.get("result", "")
            if result_text:
                if data.get("is_error"):
                    result["cli_error_message"] = result_text
                else:
                    accumulated_output.append(result_text)
                    asyncio.create_task(output_queue.put(result_text))

        return result if result else None

    def _handle_assistant_message(
        self,
        data: dict[str, object],
        task_id: str,
        accumulated_output: list[str],
        clean_output: list[str],
        output_queue: asyncio.Queue[str | None],
        result: dict[str, float | int | str | bool | None],
    ) -> None:
        error_type = data.get("error")
        message = data.get("message", {})
        if not isinstance(message, dict):
            return

        content_blocks = message.get("content", [])
        if not isinstance(content_blocks, list):
            return

        for block in content_blocks:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")
            if block_type == "text":
                text_content = block.get("text", "")
                if text_content:
                    if error_type:
                        result["cli_error_message"] = f"{text_content} (error type: {error_type})"
                    else:
                        sanitized = sanitize_sensitive_content(text_content[:500])
                        logger.info("assistant_text", task_id=task_id, text=sanitized)

            elif block_type == "tool_use":
                tool_name = block.get("name", "unknown")
                tool_input = block.get("input", {})
                tool_log = f"\n[TOOL] Using {tool_name}\n"

                if isinstance(tool_input, dict):
                    if "command" in tool_input:
                        tool_log += f"  Command: {tool_input['command']}\n"
                    elif "description" in tool_input:
                        tool_log += f"  {tool_input['description']}\n"

                accumulated_output.append(tool_log)
                asyncio.create_task(output_queue.put(tool_log))

    def _determine_error_message(
        self, returncode: int, cli_error_message: str | None, stderr_lines: list[str]
    ) -> str | None:
        if returncode == 0:
            return None

        if cli_error_message:
            return cli_error_message

        if stderr_lines:
            cleaned_lines = [line for line in stderr_lines if not line.startswith("[LOG]") and line.strip()]
            if cleaned_lines:
                return "\n".join(cleaned_lines) + f"\n\n(Exit code: {returncode})"
            return "\n".join(stderr_lines) + f"\n\n(Exit code: {returncode})"

        return f"Exit code: {returncode}"
