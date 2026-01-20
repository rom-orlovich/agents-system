"""Claude Code CLI runner with streaming output.

This module provides utilities for running Claude Code CLI with:
- Real-time streaming output
- Structured logging
- PR URL extraction
- Common patterns shared between agents

Usage:
    from shared.claude_runner import run_claude_streaming, extract_pr_url
    
    result = await run_claude_streaming(
        prompt="Execute the task...",
        working_dir=Path("/path/to/agent"),
        timeout=600,
        allowed_tools="Read,Edit,Bash,mcp__github",
        logger=my_logger
    )
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncIterator
import logging


@dataclass
class ClaudeEvent:
    """A single event from Claude Code streaming output."""
    event_type: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaudeResult:
    """Result from running Claude Code CLI."""
    success: bool
    output: str
    error: Optional[str] = None
    events: List[ClaudeEvent] = field(default_factory=list)
    duration_seconds: float = 0.0
    pr_url: Optional[str] = None
    return_code: int = 0


def extract_pr_url(output: str) -> Optional[str]:
    """Extract GitHub PR URL from Claude's output.
    
    Args:
        output: Claude Code output text
        
    Returns:
        PR URL if found, None otherwise
    """
    pattern = r"https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/pull/\d+"
    match = re.search(pattern, output)
    return match.group(0) if match else None


def extract_commit_sha(output: str) -> Optional[str]:
    """Extract commit SHA from Claude's output.
    
    Args:
        output: Claude Code output text
        
    Returns:
        Commit SHA if found (7+ hex chars)
    """
    pattern = r"\b[a-f0-9]{7,40}\b"
    match = re.search(pattern, output)
    return match.group(0) if match else None


async def stream_process_output(
    process: asyncio.subprocess.Process,
    logger: logging.Logger,
    prefix: str = "Claude"
) -> AsyncIterator[str]:
    """Stream process stdout line by line with logging.
    
    Yields each line as it becomes available, logging in real-time.
    
    Args:
        process: The subprocess to stream from
        logger: Logger for real-time output
        prefix: Log prefix for identifying output source
        
    Yields:
        Each line of output as it's received
    """
    async for line in process.stdout:
        decoded = line.decode("utf-8").rstrip()
        if decoded:
            if prefix:
                logger.info(f"[{prefix}] {decoded}")
            yield decoded


async def run_claude_streaming(
    prompt: str,
    working_dir: Path,
    timeout: int,
    allowed_tools: str,
    logger: logging.Logger,
    stream_json: bool = False
) -> ClaudeResult:
    """Run Claude Code CLI with real-time streaming output.
    
    Claude Code automatically loads from working_dir:
    - .claude/CLAUDE.md for instructions
    - .claude/mcp.json for MCP servers
    
    Args:
        prompt: The task prompt for Claude
        working_dir: Directory to run from (should contain .claude/)
        timeout: Timeout in seconds
        allowed_tools: Comma-separated list of allowed tools
        logger: Logger for streaming output
        stream_json: If True, use --output-format stream-json for structured events
        
    Returns:
        ClaudeResult with output, events, and metadata
    """
    start_time = datetime.now()
    events: List[ClaudeEvent] = []
    output_lines: List[str] = []
    
    try:
        # Verify .claude/CLAUDE.md exists
        claude_md = working_dir / ".claude" / "CLAUDE.md"
        if claude_md.exists():
            logger.info(f"✓ CLAUDE.md found at {claude_md}")
        else:
            logger.warning(f"⚠ No CLAUDE.md at {claude_md}")
        
        # Build command
        output_format = "stream-json" if stream_json else "text"
        cmd = [
            "claude",
            "-p",  # Print mode (headless)
            "--output-format", output_format,
            "--dangerously-skip-permissions",
        ]
        
        if stream_json:
            cmd.append("--verbose")
            
        cmd.extend([
            "--allowedTools", allowed_tools,
            "--",  # Separate flags from prompt
            prompt
        ])
        
        logger.info("=" * 60)
        logger.info("CLAUDE CODE CLI STARTING")
        logger.info("=" * 60)
        logger.info(f"Working dir: {working_dir}")
        logger.info(f"Timeout: {timeout}s")
        logger.info(f"Tools: {allowed_tools}")
        logger.info(f"Prompt preview: {prompt}")
        logger.info("=" * 60)
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(working_dir),
            limit=10 * 1024 * 1024  # Increase buffer limit to 10MB
        )
        
        logger.info(f"Process started, PID: {process.pid}")
        
        # Stream stdout in real-time
        if stream_json:
            # Parse streaming JSON events
            # Use prefix=None to handle logging ourselves based on event type
            async for line in stream_process_output(process, logger, prefix=None):
                try:
                    event_data = json.loads(line)
                    etype = event_data.get("type", "unknown")
                    content = event_data.get("content", "")
                    
                    if etype == "thought":
                        if content:
                            logger.info(f"🧠 [Claude Thinking] {content}")
                    elif etype == "tool_use":
                        name = event_data.get("name")
                        args = event_data.get("input")
                        logger.info(f"🛠️ [Claude Tool Use] {name}({args})")
                    elif etype == "tool_result":
                        name = event_data.get("name")
                        logger.info(f"✅ [Claude Tool Result] {name}")
                    elif etype == "text":
                        if content:
                            logger.info(f"💬 [Claude Text] {content}")
                            output_lines.append(content)
                    elif etype == "result":
                        result_text = event_data.get("result", "")
                        is_error = event_data.get("is_error", False)
                        if is_error:
                            logger.error(f"❌ [Claude Result Error] {result_text}")
                            output_lines.append(f"ERROR: {result_text}")
                        else:
                            logger.info(f"✅ [Claude Result] {result_text}")
                            output_lines.append(result_text)
                    elif etype == "error":
                        logger.error(f"❌ [Claude Error] {content}")
                    else:
                        # Catch-all for other event types (user_message, assistant_message, etc.)
                        logger.info(f"ℹ️ [Claude Event: {etype}] {str(event_data)[:200]}")
                        if content:
                             output_lines.append(f"[{etype}] {content}")
                    
                    event = ClaudeEvent(
                        event_type=etype,
                        content=content,
                        raw=event_data
                    )
                    events.append(event)
                except json.JSONDecodeError:
                    # In case of non-JSON mixed in or broken lines
                    logger.warning(f"⚠ Non-JSON output in stream: {line}")
                    output_lines.append(line)
        else:
            # Traditional text output
            async for line in stream_process_output(process, logger, "Claude"):
                output_lines.append(line)
        
        # Wait for process to complete with timeout
        try:
            await asyncio.wait_for(
                process.wait(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"TIMEOUT after {timeout}s")
            return ClaudeResult(
                success=False,
                output="\n".join(output_lines),
                error=f"Timeout after {timeout}s",
                events=events,
                duration_seconds=duration,
                return_code=-1
            )
        
        # Read any remaining stderr
        stderr_output = ""
        if process.stderr:
            stderr_data = await process.stderr.read()
            stderr_output = stderr_data.decode("utf-8")
            if stderr_output:
                logger.warning(f"[Claude stderr] {stderr_output}")
        
        duration = (datetime.now() - start_time).total_seconds()
        output = "\n".join(output_lines)
        
        logger.info("=" * 60)
        logger.info("CLAUDE CODE CLI COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Return code: {process.returncode}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"Output lines: {len(output_lines)}")
        logger.info(f"Events: {len(events)}")
        
        # Try to parse final JSON output if not streaming
        if not stream_json and output_lines:
            try:
                # Claude may output JSON at the end
                result_data = json.loads(output)
                output = result_data.get("result", output)
            except json.JSONDecodeError:
                pass
        
        # Extract PR URL
        pr_url = extract_pr_url(output)
        if pr_url:
            logger.info(f"✓ PR URL found: {pr_url}")
        
        return ClaudeResult(
            success=process.returncode == 0,
            output=output,
            error=stderr_output if stderr_output else (output if process.returncode != 0 else None),
            events=events,
            duration_seconds=duration,
            pr_url=pr_url,
            return_code=process.returncode
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ClaudeResult(
            success=False,
            output="\n".join(output_lines),
            error=str(e),
            events=events,
            duration_seconds=duration,
            return_code=-1
        )


async def run_claude_simple(
    prompt: str,
    working_dir: Path,
    timeout: int,
    allowed_tools: str,
    logger: logging.Logger
) -> ClaudeResult:
    """Simplified Claude Code runner - waits for completion without streaming.
    
    Use this when you don't need real-time output visibility.
    
    Args:
        prompt: The task prompt for Claude
        working_dir: Directory to run from
        timeout: Timeout in seconds
        allowed_tools: Comma-separated list of allowed tools
        logger: Logger for output
        
    Returns:
        ClaudeResult with output and metadata
    """
    start_time = datetime.now()
    
    try:
        cmd = [
            "claude",
            "-p",
            "--output-format", "json",
            "--dangerously-skip-permissions",
            "--allowedTools", allowed_tools,
            "--",  # Separate flags from prompt
            prompt
        ]
        
        logger.info(f"Running Claude Code CLI (simple mode)")
        logger.info(f"Working dir: {working_dir}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(working_dir),
            limit=10 * 1024 * 1024  # Increase buffer limit to 10MB
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        
        output = stdout.decode("utf-8")
        error = stderr.decode("utf-8")
        duration = (datetime.now() - start_time).total_seconds()
        
        # Try to extract result from JSON
        try:
            result_data = json.loads(output)
            output = result_data.get("result", output)
        except json.JSONDecodeError:
            pass
        
        return ClaudeResult(
            success=process.returncode == 0,
            output=output,
            error=error if process.returncode != 0 else None,
            duration_seconds=duration,
            pr_url=extract_pr_url(output),
            return_code=process.returncode
        )
        
    except asyncio.TimeoutError:
        duration = (datetime.now() - start_time).total_seconds()
        return ClaudeResult(
            success=False,
            output="",
            error=f"Timeout after {timeout}s",
            duration_seconds=duration,
            return_code=-1
        )
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        return ClaudeResult(
            success=False,
            output="",
            error=str(e),
            duration_seconds=duration,
            return_code=-1
        )
