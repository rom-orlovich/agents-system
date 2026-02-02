import asyncio
import json
import os
from pathlib import Path
import structlog

from cli.base import CLIResult
from cli.sanitization import sanitize_sensitive_content, contains_sensitive_data

logger = structlog.get_logger()


class ClaudeCLIRunner:
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

        logger.info(
            "starting_claude_cli", task_id=task_id, working_dir=str(working_dir)
        )

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

        await output_queue.put(f"[CLI] Claude process started (PID: {process.pid})\n")

        accumulated_output: list[str] = []
        clean_output: list[str] = []
        cost_usd = 0.0
        input_tokens = 0
        output_tokens = 0
        cli_error_message: str | None = None
        has_streaming_output = False
        stderr_lines: list[str] = []

        try:

            async def read_stdout() -> None:
                nonlocal cost_usd, input_tokens, output_tokens, cli_error_message
                nonlocal has_streaming_output

                if not process.stdout:
                    return

                async for line in process.stdout:
                    line_str = line.decode(errors="replace").rstrip("\n\r")
                    if not line_str:
                        continue

                    try:
                        data = json.loads(line_str)
                        await self._handle_json_event(
                            data,
                            accumulated_output,
                            clean_output,
                            output_queue,
                            task_id,
                            has_streaming_output,
                        )

                        msg_type = data.get("type")
                        if msg_type == "stream_event":
                            event = data.get("event", {})
                            if event.get("type") == "content_block_delta":
                                has_streaming_output = True

                        if msg_type == "result":
                            cost_usd = data.get(
                                "total_cost_usd", data.get("cost_usd", 0.0)
                            )
                            usage = data.get("usage", {})
                            input_tokens = usage.get("input_tokens", 0)
                            output_tokens = usage.get("output_tokens", 0)
                            if data.get("is_error"):
                                cli_error_message = data.get("result", "")

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
                process.returncode or 0, stderr_lines, cli_error_message
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

            logger.error("claude_cli_timeout", task_id=task_id, timeout=timeout_seconds)

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

            logger.error(
                "claude_cli_error", task_id=task_id, error=str(e), exc_info=True
            )

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
            "claude",
            "-p",
            "--output-format",
            "stream-json",
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

    async def _handle_json_event(
        self,
        data: dict,
        accumulated_output: list[str],
        clean_output: list[str],
        output_queue: asyncio.Queue[str | None],
        task_id: str,
        has_streaming_output: bool,
    ) -> None:
        msg_type = data.get("type")

        if msg_type == "init":
            init_content = data.get("content", "")
            if init_content:
                accumulated_output.append(init_content)
                await output_queue.put(init_content)

        elif msg_type == "assistant":
            await self._handle_assistant_message(
                data,
                accumulated_output,
                clean_output,
                output_queue,
                task_id,
                has_streaming_output,
            )

        elif msg_type == "user":
            await self._handle_user_message(
                data, accumulated_output, output_queue, task_id
            )

        elif msg_type == "stream_event":
            event = data.get("event", {})
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        accumulated_output.append(text)
                        clean_output.append(text)
                        await output_queue.put(text)

        elif msg_type == "result":
            result_text = data.get("result", "")
            if result_text and not data.get("is_error"):
                accumulated_output.append(result_text)
                await output_queue.put(result_text)

    async def _handle_assistant_message(
        self,
        data: dict,
        accumulated_output: list[str],
        clean_output: list[str],
        output_queue: asyncio.Queue[str | None],
        task_id: str,
        has_streaming_output: bool,
    ) -> None:
        message = data.get("message", {})
        content_blocks = message.get("content", [])

        for block in content_blocks:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")
            if block_type == "text":
                text_content = block.get("text", "")
                if text_content and not has_streaming_output:
                    clean_output.append(text_content)

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
                await output_queue.put(tool_log)

    async def _handle_user_message(
        self,
        data: dict,
        accumulated_output: list[str],
        output_queue: asyncio.Queue[str | None],
        task_id: str,
    ) -> None:
        message = data.get("message", {})
        content = message.get("content", []) if isinstance(message, dict) else []

        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                tool_content = block.get("content", "")
                is_error = block.get("is_error", False)
                if tool_content:
                    if contains_sensitive_data(tool_content):
                        tool_content = sanitize_sensitive_content(tool_content)
                    prefix = "[TOOL ERROR] " if is_error else "[TOOL RESULT]\n"
                    result_log = f"{prefix}{tool_content}\n"
                    accumulated_output.append(result_log)
                    await output_queue.put(result_log)

    def _determine_error_message(
        self,
        returncode: int,
        stderr_lines: list[str],
        cli_error_message: str | None,
    ) -> str | None:
        if returncode == 0:
            return None

        if cli_error_message:
            return cli_error_message

        if stderr_lines:
            cleaned_lines = [
                line
                for line in stderr_lines
                if not line.startswith("[LOG]") and line.strip()
            ]
            if cleaned_lines:
                return "\n".join(cleaned_lines) + f"\n\n(Exit code: {returncode})"
            return "\n".join(stderr_lines) + f"\n\n(Exit code: {returncode})"

        return f"Exit code: {returncode}"
