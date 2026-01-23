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

    Returns:
        CLIResult with output, cost, and token counts

    References:
        https://code.claude.com/docs/en/sub-agents
    """

    # Build the command (matching official Claude CLI documentation)
    cmd = [
        "claude",
        "-p",                         # Print mode (headless) - NOT --print!
        "--output-format", "json",    # JSON output for parsing
        "--dangerously-skip-permissions",  # Skip permission prompts
    ]

    # Add optional model
    if model:
        cmd.extend(["--model", model])

    # Add allowed tools (pre-approved permissions for headless mode)
    if allowed_tools:
        cmd.extend(["--allowedTools", allowed_tools])

    # Add sub-agents definition (JSON)
    if agents:
        cmd.extend(["--agents", agents])

    # Separator and prompt
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
            "CLAUDE_TASK_ID": task_id,  # For status monitoring
        }
    )

    accumulated_output = []
    cost_usd = 0.0
    input_tokens = 0
    output_tokens = 0

    try:
        # Stream stdout in real-time
        async def read_stdout():
            nonlocal cost_usd, input_tokens, output_tokens

            if not process.stdout:
                return

            async for line in process.stdout:
                line_str = line.decode().strip()
                if not line_str:
                    continue

                try:
                    # Parse JSON output from Claude CLI
                    data = json.loads(line_str)

                    if data.get("type") == "content":
                        # Text output - stream to queue
                        chunk = data.get("content", "")
                        accumulated_output.append(chunk)
                        await output_queue.put(chunk)

                    elif data.get("type") == "result":
                        # Final result with metrics
                        # Claude CLI uses total_cost_usd and nested usage object
                        cost_usd = data.get("total_cost_usd", data.get("cost_usd", 0.0))
                        usage = data.get("usage", {})
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)

                        # Also extract the result text if available
                        result_text = data.get("result", "")
                        if result_text:
                            accumulated_output.append(result_text)
                            await output_queue.put(result_text)

                except json.JSONDecodeError:
                    # Plain text output
                    accumulated_output.append(line_str)
                    await output_queue.put(line_str)

        # Stream stderr (subagent logs, diagnostics, errors)
        stderr_lines = []
        async def read_stderr():
            nonlocal stderr_lines
            if not process.stderr:
                return

            async for line in process.stderr:
                line_str = line.decode().strip()
                if not line_str:
                    continue

                # Store stderr for error reporting
                stderr_lines.append(line_str)

                # Prefix stderr with [LOG] for visibility
                log_line = f"[LOG] {line_str}"
                accumulated_output.append(log_line + "\n")
                await output_queue.put(log_line + "\n")

        # Run both streams concurrently with timeout
        await asyncio.wait_for(
            asyncio.gather(read_stdout(), read_stderr()),
            timeout=timeout_seconds
        )
        await process.wait()

        # Signal end of stream
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

        # Build error message if CLI failed
        error_msg = None
        if process.returncode != 0:
            if stderr_lines:
                # Capture ALL stderr lines for complete error reporting
                full_stderr = "\n".join(stderr_lines)
                
                # Extract meaningful error messages (prioritize actual error text over exit code)
                # Look for common error patterns
                error_text = full_stderr
                
                # Remove common noise patterns
                cleaned_lines = []
                for line in stderr_lines:
                    # Skip verbose log prefixes but keep actual errors
                    if not line.startswith("[LOG]") and line.strip():
                        cleaned_lines.append(line)
                
                if cleaned_lines:
                    # Use cleaned error text as primary message
                    error_text = "\n".join(cleaned_lines)
                    # Include exit code as secondary information
                    error_msg = f"{error_text}\n\n(Exit code: {process.returncode})"
                else:
                    # Fallback to full stderr if cleaning removed everything
                    error_msg = f"{full_stderr}\n\n(Exit code: {process.returncode})"
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
        await process.wait()  # ✅ CRITICAL: Wait for zombie cleanup
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
            await process.wait()  # ✅ CRITICAL: Wait for zombie cleanup
        await output_queue.put(None)
        return CLIResult(
            success=False,
            output="".join(accumulated_output),
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=str(e)
        )
