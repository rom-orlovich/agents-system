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
) -> CLIResult:
    """
    Execute Claude Code CLI in headless mode.

    This is the actual subprocess execution - same as today's implementation.

    Args:
        prompt: The task prompt to send to Claude
        working_dir: Directory to run from (determines which CLAUDE.md is read)
        output_queue: Queue to stream output chunks to
        task_id: Task ID for monitoring
        timeout_seconds: Maximum execution time

    Returns:
        CLIResult with output, cost, and token counts
    """

    # Build the command (matching official Claude CLI documentation)
    cmd = [
        "claude",
        "-p",                         # Print mode (headless) - NOT --print!
        "--output-format", "json",    # JSON output for parsing
        "--dangerously-skip-permissions",  # Skip permission prompts
        "--",                         # Separator between flags and prompt
        prompt,                       # The prompt/task
    ]

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
        async def read_stream():
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
                        cost_usd = data.get("cost_usd", 0.0)
                        input_tokens = data.get("input_tokens", 0)
                        output_tokens = data.get("output_tokens", 0)

                except json.JSONDecodeError:
                    # Plain text output
                    accumulated_output.append(line_str)
                    await output_queue.put(line_str)

        # Run with timeout
        await asyncio.wait_for(read_stream(), timeout=timeout_seconds)
        await process.wait()

        # Signal end of stream
        await output_queue.put(None)

        logger.info(
            "Claude CLI completed",
            task_id=task_id,
            success=process.returncode == 0,
            cost_usd=cost_usd,
        )

        return CLIResult(
            success=process.returncode == 0,
            output="".join(accumulated_output),
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=None if process.returncode == 0 else f"Exit code: {process.returncode}"
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
