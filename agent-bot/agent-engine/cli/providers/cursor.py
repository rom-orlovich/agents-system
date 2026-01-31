import asyncio
import json
import os
from pathlib import Path
import structlog

from cli.base import CLIResult
from cli.sanitization import sanitize_sensitive_content, contains_sensitive_data

logger = structlog.get_logger()


class CursorCLIRunner:
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
        mode: str | None = None,
        force: bool = True,
    ) -> CLIResult:
        cmd = self._build_command(prompt, model, mode, force)

        logger.info(
            "starting_cursor_cli", task_id=task_id, working_dir=str(working_dir)
        )

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
        session_id: str = ""

        try:

            async def read_stdout() -> None:
                nonlocal cost_usd, input_tokens, output_tokens, session_id

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
                        )

                        if data.get("session_id"):
                            session_id = data["session_id"]

                        if data.get("type") == "result":
                            duration_ms = data.get("duration_ms", 0)
                            logger.info(
                                "cursor_result",
                                task_id=task_id,
                                duration_ms=duration_ms,
                                is_error=data.get("is_error", False),
                            )

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
                session_id=session_id,
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

            logger.error(
                "cursor_cli_error", task_id=task_id, error=str(e), exc_info=True
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
        mode: str | None,
        force: bool,
    ) -> list[str]:
        cmd = [
            "agent",
            "-p",
            "--output-format",
            "stream-json",
        ]

        if force:
            cmd.append("-f")

        if model:
            cmd.extend(["-m", model])

        if mode and mode in ("agent", "plan", "ask"):
            cmd.extend(["--mode", mode])

        cmd.append(prompt)

        return cmd

    async def _handle_json_event(
        self,
        data: dict,
        accumulated_output: list[str],
        clean_output: list[str],
        output_queue: asyncio.Queue[str | None],
        task_id: str,
    ) -> None:
        event_type = data.get("type")

        if event_type == "system":
            subtype = data.get("subtype")
            if subtype == "init":
                model = data.get("model", "unknown")
                init_log = f"[INIT] Session started with model: {model}\n"
                accumulated_output.append(init_log)
                await output_queue.put(init_log)

        elif event_type == "user":
            pass

        elif event_type == "assistant":
            message = data.get("message", {})
            content_blocks = message.get("content", [])
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        accumulated_output.append(text)
                        clean_output.append(text)
                        await output_queue.put(text)

        elif event_type == "tool_call":
            subtype = data.get("subtype")
            tool_call = data.get("tool_call", {})

            if subtype == "started":
                tool_name = self._extract_tool_name(tool_call)
                tool_log = f"\n[TOOL] Starting: {tool_name}\n"
                accumulated_output.append(tool_log)
                await output_queue.put(tool_log)

            elif subtype == "completed":
                tool_name = self._extract_tool_name(tool_call)
                result = self._extract_tool_result(tool_call)
                if result:
                    if contains_sensitive_data(result):
                        result = sanitize_sensitive_content(result)
                    result_log = f"[TOOL RESULT] {tool_name}: {result[:500]}\n"
                    accumulated_output.append(result_log)
                    await output_queue.put(result_log)

        elif event_type == "result":
            result_text = data.get("result", "")
            if result_text and not data.get("is_error"):
                clean_output.append(result_text)

    def _extract_tool_name(self, tool_call: dict) -> str:
        for key in tool_call:
            if key.endswith("ToolCall"):
                return key.replace("ToolCall", "")
        return "unknown"

    def _extract_tool_result(self, tool_call: dict) -> str:
        for key, value in tool_call.items():
            if key.endswith("ToolCall") and isinstance(value, dict):
                result = value.get("result", {})
                if isinstance(result, dict):
                    if "success" in result:
                        success = result["success"]
                        if isinstance(success, dict):
                            return success.get("content", str(success))
                        return str(success)
                    if "error" in result:
                        return f"Error: {result['error']}"
                return str(result)
        return ""

    def _determine_error_message(
        self, returncode: int, stderr_lines: list[str]
    ) -> str | None:
        if returncode == 0:
            return None

        if stderr_lines:
            return "\n".join(stderr_lines) + f"\n\n(Exit code: {returncode})"

        return f"Exit code: {returncode}"
