"""Execute Claude Code CLI in headless mode."""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


def sanitize_sensitive_content(content: str) -> str:
    """
    Sanitize sensitive information from content before logging.
    
    Masks API tokens, passwords, and other credentials.
    """
    if not content:
        return content
    
    sensitive_patterns = [
        (r'(JIRA_API_TOKEN|JIRA_EMAIL|GITHUB_TOKEN|SLACK_BOT_TOKEN|SLACK_WEBHOOK_SECRET|GITHUB_WEBHOOK_SECRET|JIRA_WEBHOOK_SECRET)\s*=\s*([^\s\n]+)', r'\1=***REDACTED***'),
        (r'(password|passwd|pwd|token|secret|api_key|apikey|access_token|refresh_token)\s*[:=]\s*([^\s\n]+)', r'\1=***REDACTED***', re.IGNORECASE),
        (r'(Authorization:\s*Bearer\s+)([^\s\n]+)', r'\1***REDACTED***'),
        (r'(Authorization:\s*Basic\s+)([^\s\n]+)', r'\1***REDACTED***'),
        (r'(["\']?token["\']?\s*[:=]\s*["\']?)([^"\'\s\n]+)(["\']?)', r'\1***REDACTED***\3', re.IGNORECASE),
        (r'(["\']?password["\']?\s*[:=]\s*["\']?)([^"\'\s\n]+)(["\']?)', r'\1***REDACTED***\3', re.IGNORECASE),
    ]
    
    sanitized = content
    for pattern in sensitive_patterns:
        if len(pattern) == 2:
            sanitized = re.sub(pattern[0], pattern[1], sanitized)
        else:
            sanitized = re.sub(pattern[0], pattern[1], sanitized, flags=pattern[2])
    
    return sanitized


def contains_sensitive_data(content: str) -> bool:
    """
    Check if content contains sensitive data patterns.
    
    Used to determine if content should be sanitized before sending to models.
    """
    if not content:
        return False
    
    sensitive_indicators = [
        r'JIRA_API_TOKEN\s*=',
        r'GITHUB_TOKEN\s*=',
        r'SLACK_BOT_TOKEN\s*=',
        r'password\s*[:=]',
        r'token\s*[:=]',
        r'secret\s*[:=]',
        r'Authorization:\s*(Bearer|Basic)',
    ]
    
    content_lower = content.lower()
    for pattern in sensitive_indicators:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return True
    
    return False


@dataclass
class CLIResult:
    success: bool
    output: str
    clean_output: str
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
    clean_output = []
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
                                            sanitized_text = sanitize_sensitive_content(text_content[:500])
                                            logger.info("assistant_text", task_id=task_id, text=sanitized_text)
                                            accumulated_output.append(text_content)
                                            clean_output.append(text_content)
                                            await output_queue.put(text_content)
                                elif block_type == "tool_use":
                                    # Log tool usage (only to full output, not clean output)
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
                                    if contains_sensitive_data(tool_content):
                                        sanitized_content = sanitize_sensitive_content(tool_content)
                                        prefix = "[TOOL ERROR] " if is_error else "[TOOL RESULT]\n"
                                        result_log = f"{prefix}{sanitized_content}\n"
                                        accumulated_output.append(result_log)
                                        await output_queue.put(result_log)
                                    else:
                                        prefix = "[TOOL ERROR] " if is_error else "[TOOL RESULT]\n"
                                        result_log = f"{prefix}{tool_content}\n"
                                        accumulated_output.append(result_log)
                                        await output_queue.put(result_log)
                                    
                                    sanitized_preview = sanitize_sensitive_content(tool_content[:200])
                                    logger.info("tool_result", task_id=task_id, is_error=is_error, content_preview=sanitized_preview)
                    
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
                        
                        result_text = data.get("result", "")
                        if result_text:
                            if data.get("is_error"):
                                cli_error_message = result_text
                            else:
                                accumulated_output.append(result_text)
                                await output_queue.put(result_text)



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

        sanitized_stderr = None
        if stderr_lines:
            stderr_preview = "\n".join(stderr_lines[-3:])
            sanitized_stderr = sanitize_sensitive_content(stderr_preview)
        
        logger.info(
            "Claude CLI completed",
            task_id=task_id,
            success=process.returncode == 0,
            cost_usd=cost_usd,
            returncode=process.returncode,
            has_stderr=len(stderr_lines) > 0,
            stderr_preview=sanitized_stderr
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
        
        clean_output_text = "".join(clean_output) if clean_output else ""
        
        from core.config import settings
        if task_id and settings.debug_save_task_logs:
            try:
                log_dir = Path(".log")
                log_dir.mkdir(exist_ok=True)
                log_file = log_dir / f"{task_id}.log"
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write(f"Task ID: {task_id}\n")
                    f.write(f"Success: {process.returncode == 0}\n")
                    f.write(f"Cost USD: {cost_usd}\n")
                    f.write(f"Input Tokens: {input_tokens}\n")
                    f.write(f"Output Tokens: {output_tokens}\n")
                    if error_msg:
                        f.write(f"\nError: {error_msg}\n")
                    f.write("\n" + "="*80 + "\n")
                    f.write("FULL OUTPUT:\n")
                    f.write("="*80 + "\n")
                    f.write("".join(accumulated_output))
                logger.info("task_log_saved", task_id=task_id, log_file=str(log_file))
            except Exception as e:
                logger.warning("task_log_save_failed", task_id=task_id, error=str(e))
        
        return CLIResult(
            success=process.returncode == 0,
            output="".join(accumulated_output),
            clean_output=clean_output_text,
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
        clean_output_text = "".join(clean_output) if clean_output else ""
        return CLIResult(
            success=False,
            output="".join(accumulated_output),
            clean_output=clean_output_text,
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
        clean_output_text = "".join(clean_output) if clean_output else ""
        return CLIResult(
            success=False,
            output="".join(accumulated_output),
            clean_output=clean_output_text,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=str(e)
        )
