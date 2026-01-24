"""Execute Claude Code CLI in headless mode."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class CLIResult:
    """Result from Claude CLI execution."""
    success: bool
    output: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    error: Optional[str] = None


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
    """
    Execute Claude Code CLI in headless mode.

    Args:
        prompt: The task prompt to send to Claude
        working_dir: Directory to run from (determines which CLAUDE.md is read)
        output_queue: Queue to stream output chunks to
        task_id: Task ID for monitoring
        timeout_seconds: Maximum execution time
        model: Optional model name (e.g., "opus", "sonnet")
        allowed_tools: Comma-separated list of allowed tools (e.g., "Read,Edit,Bash")
        agents: JSON string defining sub-agents for the session
        debug_mode: Optional debug filter (e.g., "api", "!statsig", empty for all)

    Returns:
        CLIResult with output, cost, and token counts

    References:
        https://code.claude.com/docs/en/sub-agents
    """

    cmd = [
        "claude",
        "-p",
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
        "--include-partial-messages",  # Stream partial message chunks as they arrive
    ]
    
    # Add debug mode for detailed logging
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

    logger.info("Starting Claude CLI", task_id=task_id, working_dir=str(working_dir))

    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(working_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            **os.environ,
            "CLAUDE_TASK_ID": task_id,
            "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
        }
    )
    
    # Immediately notify that CLI has started
    await output_queue.put(f"[CLI] Process started (PID: {process.pid})\n")

    accumulated_output = []
    cost_usd = 0.0
    input_tokens = 0
    output_tokens = 0
    cli_error_message = None  # Capture error from JSON response

    try:
        async def read_stdout():
            nonlocal cost_usd, input_tokens, output_tokens, cli_error_message

            if not process.stdout:
                return

            async for line in process.stdout:
                line_bytes = line
                line_str = line_bytes.decode(errors='replace').rstrip('\n\r')
                
                if not line_str:
                    continue

                try:
                    data = json.loads(line_str)

                    msg_type = data.get("type")
                    
                    if msg_type == "init":
                        init_content = data.get("content", "")
                        if init_content:
                            accumulated_output.append(init_content)
                            await output_queue.put(init_content)
                    
                    elif msg_type == "assistant":
                        # Extract text and tool_use content from assistant message
                        error_type = data.get("error")
                        message = data.get("message", {})
                        content_blocks = message.get("content", [])
                        
                        # Extract all content blocks
                        for block in content_blocks:
                            if isinstance(block, dict):
                                block_type = block.get("type")
                                if block_type == "text":
                                    text_content = block.get("text", "")
                                    if text_content:
                                        if error_type:
                                            cli_error_message = f"{text_content} (error type: {error_type})"
                                        else:
                                            logger.info("assistant_text", task_id=task_id, text=text_content[:500])
                                            accumulated_output.append(text_content)
                                            await output_queue.put(text_content)
                                elif block_type == "tool_use":
                                    # Log tool usage
                                    tool_name = block.get("name", "unknown")
                                    tool_input = block.get("input", {})
                                    tool_log = f"\n[TOOL] Using {tool_name}\n"
                                    cmd = None
                                    if isinstance(tool_input, dict):
                                        if "command" in tool_input:
                                            cmd = tool_input['command']
                                            tool_log += f"  Command: {cmd}\n"
                                        elif "description" in tool_input:
                                            tool_log += f"  {tool_input['description']}\n"
                                    logger.info("tool_use", task_id=task_id, tool=tool_name, command=cmd)
                                    accumulated_output.append(tool_log)
                                    await output_queue.put(tool_log)
                    
                    elif msg_type == "user":
                        # Tool results
                        message = data.get("message", {})
                        content = message.get("content", []) if isinstance(message, dict) else data.get("content", [])
                        for block in content if isinstance(content, list) else []:
                            if isinstance(block, dict) and block.get("type") == "tool_result":
                                tool_content = block.get("content", "")
                                is_error = block.get("is_error", False)
                                if tool_content:
                                    prefix = "[TOOL ERROR] " if is_error else "[TOOL RESULT]\n"
                                    # Truncate long tool results
                                    if len(tool_content) > 2000:
                                        tool_content = tool_content[:2000] + "\n... (truncated)"
                                    result_log = f"{prefix}{tool_content}\n"
                                    logger.info("tool_result", task_id=task_id, is_error=is_error, content_preview=tool_content[:200])
                                    accumulated_output.append(result_log)
                                    await output_queue.put(result_log)
                    
                    elif msg_type == "stream_event":
                        # Streaming chunks - only show text deltas
                        event = data.get("event", {})
                        if event.get("type") == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    accumulated_output.append(text)
                                    await output_queue.put(text)
                    
                    elif msg_type == "message":
                        role = data.get("role", "")
                        content = data.get("content", "")
                        if content:
                            formatted = f"[{role}]: {content}\n" if role else f"{content}\n"
                            accumulated_output.append(formatted)
                            await output_queue.put(formatted)
                    
                    elif msg_type == "content":
                        chunk = data.get("content", "")
                        if chunk:
                            logger.debug("chunk_received", task_id=task_id, chunk_len=len(chunk))
                            accumulated_output.append(chunk)
                            await output_queue.put(chunk)
                    
                    elif msg_type == "result":
                        cost_usd = data.get("total_cost_usd", data.get("cost_usd", 0.0))
                        usage = data.get("usage", {})
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        
                        # Capture error from result if is_error is true
                        if data.get("is_error"):
                            result_text = data.get("result", "")
                            if result_text:
                                cli_error_message = result_text



                except json.JSONDecodeError as e:
                    accumulated_output.append(line_str + "\n")
                    await output_queue.put(line_str + "\n")

        stderr_lines = []
        async def read_stderr():
            nonlocal stderr_lines
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
            asyncio.gather(read_stdout(), read_stderr()),
            timeout=timeout_seconds
        )
        await process.wait()

        await output_queue.put(None)

        logger.info(
            "Claude CLI completed",
            task_id=task_id,
            success=process.returncode == 0,
            cost_usd=cost_usd,
            returncode=process.returncode,
            has_stderr=len(stderr_lines) > 0,
            stderr_preview="\n".join(stderr_lines[-3:]) if stderr_lines else None
        )

        error_msg = None
        if process.returncode != 0:
            # Priority 1: Use error captured from JSON response (most informative)
            if cli_error_message:
                error_msg = cli_error_message
            # Priority 2: Use stderr if available
            elif stderr_lines:
                full_stderr = "\n".join(stderr_lines)
                
                error_text = full_stderr
                
                cleaned_lines = []
                for line in stderr_lines:
                    if not line.startswith("[LOG]") and line.strip():
                        cleaned_lines.append(line)
                
                if cleaned_lines:
                    error_text = "\n".join(cleaned_lines)
                    error_msg = f"{error_text}\n\n(Exit code: {process.returncode})"
                else:
                    error_msg = f"{full_stderr}\n\n(Exit code: {process.returncode})"
            # Priority 3: Generic exit code message
            else:
                error_msg = f"Exit code: {process.returncode}"
        
        return CLIResult(
            success=process.returncode == 0,
            output="".join(accumulated_output),
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=error_msg
        )

    except asyncio.TimeoutError:
        logger.error("Claude CLI timeout", task_id=task_id, timeout=timeout_seconds)
        process.kill()
        await process.wait()
        await output_queue.put(None)
        return CLIResult(
            success=False,
            output="".join(accumulated_output),
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error="Timeout exceeded"
        )
    except Exception as e:
        logger.error("Claude CLI error", task_id=task_id, error=str(e))
        if process.returncode is None:
            process.kill()
            await process.wait()
        await output_queue.put(None)
        return CLIResult(
            success=False,
            output="".join(accumulated_output),
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=str(e)
        )
