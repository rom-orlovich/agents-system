"""Unit tests for CLI runner."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core.cli_runner import run_claude_cli, CLIResult


class MockAsyncIterator:
    """Mock async iterator for subprocess stdout."""

    def __init__(self, lines):
        self.lines = lines
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.lines):
            raise StopAsyncIteration
        line = self.lines[self.index]
        self.index += 1
        return line
async def test_cli_runner_success():
    """Test successful CLI execution."""
    output_queue = asyncio.Queue()

    # Mock subprocess that outputs JSON
    mock_proc = AsyncMock()
    mock_proc.returncode = 0

    # Simulate CLI output
    output_lines = [
        b'{"type": "content", "content": "Hello"}\n',
        b'{"type": "content", "content": " World"}\n',
        b'{"type": "result", "cost_usd": 0.05, "usage": {"input_tokens": 100, "output_tokens": 50}}\n',
    ]

    mock_proc.stdout = MockAsyncIterator(output_lines)
    mock_proc.wait = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        result = await run_claude_cli(
            prompt="Test prompt",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-001",
            timeout_seconds=60
        )

    assert result.success is True
    assert result.output == "Hello World"
    assert result.cost_usd == 0.05
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.error is None

    # Check output was queued
    chunks = []
    while not output_queue.empty():
        chunk = await output_queue.get()
        if chunk is not None:
            chunks.append(chunk)

    assert chunks == ["Hello", " World"]
async def test_cli_runner_timeout():
    """Test CLI execution timeout."""
    output_queue = asyncio.Queue()

    # Mock subprocess that never completes
    mock_proc = AsyncMock()
    mock_proc.returncode = None
    mock_proc.kill = MagicMock()

    # Infinite async iterator
    class InfiniteIterator:
        def __aiter__(self):
            return self

        async def __anext__(self):
            await asyncio.sleep(0.1)
            return b'{"type": "content", "content": "..."}\n'

    mock_proc.stdout = InfiniteIterator()

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        result = await run_claude_cli(
            prompt="Test prompt",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-001",
            timeout_seconds=1  # Short timeout
        )

    assert result.success is False
    assert result.error == "Timeout exceeded"
    mock_proc.kill.assert_called_once()
async def test_cli_runner_process_error():
    """Test CLI execution with process error."""
    output_queue = asyncio.Queue()

    # Mock subprocess that fails
    mock_proc = AsyncMock()
    mock_proc.returncode = 1

    output_lines = [b'{"type": "content", "content": "Error occurred"}\n']
    mock_proc.stdout = MockAsyncIterator(output_lines)
    mock_proc.wait = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        result = await run_claude_cli(
            prompt="Test prompt",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-001",
            timeout_seconds=60
        )

    assert result.success is False
    assert result.error == "Exit code: 1"
    assert "Error occurred" in result.output
async def test_cli_runner_json_parsing():
    """Test CLI runner handles both JSON and plain text output."""
    output_queue = asyncio.Queue()

    mock_proc = AsyncMock()
    mock_proc.returncode = 0

    # Mix of JSON and plain text
    output_lines = [
        b'{"type": "content", "content": "JSON output"}\n',
        b'Plain text line\n',  # Not JSON
        b'{"type": "result", "cost_usd": 0.01, "input_tokens": 10, "output_tokens": 5}\n',
    ]

    mock_proc.stdout = MockAsyncIterator(output_lines)
    mock_proc.wait = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        result = await run_claude_cli(
            prompt="Test prompt",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-001",
            timeout_seconds=60
        )

    assert result.success is True
    assert "JSON output" in result.output
    assert "Plain text line" in result.output
