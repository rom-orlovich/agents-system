import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core.cli_runner import run_claude_cli, CLIResult


class MockAsyncIterator:
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
    output_queue = asyncio.Queue()

    mock_proc = AsyncMock()
    mock_proc.returncode = 0

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

    chunks = []
    while not output_queue.empty():
        chunk = await output_queue.get()
        if chunk is not None:
            chunks.append(chunk)

    content_chunks = [chunk for chunk in chunks if not chunk.startswith("[CLI] Process started")]
    assert content_chunks == ["Hello", " World"]
async def test_cli_runner_timeout():
    output_queue = asyncio.Queue()

    mock_proc = AsyncMock()
    mock_proc.returncode = None
    mock_proc.kill = MagicMock()

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
            timeout_seconds=1
        )

    assert result.success is False
    assert "Timeout after" in result.error or result.error == "Timeout exceeded"
    mock_proc.kill.assert_called_once()
async def test_cli_runner_process_error():
    output_queue = asyncio.Queue()

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
    output_queue = asyncio.Queue()

    mock_proc = AsyncMock()
    mock_proc.returncode = 0

    output_lines = [
        b'{"type": "content", "content": "JSON output"}\n',
        b'Plain text line\n',
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


async def test_cli_runner_logs_chunks():
    output_queue = asyncio.Queue()

    mock_proc = AsyncMock()
    mock_proc.returncode = 0

    output_lines = [
        b'{"type": "content", "content": "First chunk"}\n',
        b'{"type": "content", "content": " Second chunk"}\n',
        b'{"type": "result", "cost_usd": 0.01, "usage": {"input_tokens": 10, "output_tokens": 5}}\n',
    ]

    mock_proc.stdout = MockAsyncIterator(output_lines)
    mock_proc.stderr = MockAsyncIterator([])
    mock_proc.wait = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        result = await run_claude_cli(
            prompt="Test prompt",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-chunk-log",
            timeout_seconds=60
        )

    chunks = []
    while not output_queue.empty():
        chunk = await output_queue.get()
        if chunk is not None:
            chunks.append(chunk)
    
    content_chunks = [chunk for chunk in chunks if not chunk.startswith("[CLI] Process started")]
    assert content_chunks == ["First chunk", " Second chunk"]
    assert result.success is True


async def test_cli_runner_rate_limit_error():
    output_queue = asyncio.Queue()

    mock_proc = AsyncMock()
    mock_proc.returncode = 1

    output_lines = [
        b'{"type":"system","subtype":"init","cwd":"/app","session_id":"test-session"}\n',
        b'{"type":"assistant","message":{"content":[{"type":"text","text":"You\'ve hit your limit \\u00b7 resets 4pm (UTC)"}]},"error":"rate_limit"}\n',
        b'{"type":"result","subtype":"success","is_error":true,"result":"You\'ve hit your limit \\u00b7 resets 4pm (UTC)","total_cost_usd":0}\n',
    ]

    mock_proc.stdout = MockAsyncIterator(output_lines)
    mock_proc.stderr = MockAsyncIterator([])
    mock_proc.wait = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        result = await run_claude_cli(
            prompt="Test prompt",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-rate-limit",
            timeout_seconds=60
        )

    assert result.success is False
    assert "hit your limit" in result.error
    assert "4pm (UTC)" in result.error


async def test_cli_runner_result_field_output():
    output_queue = asyncio.Queue()

    mock_proc = AsyncMock()
    mock_proc.returncode = 0

    output_lines = [
        b'{"type": "content", "content": "Processing task"}\n',
        b'{"type": "result", "result": "Task completed successfully", "cost_usd": 0.05, "usage": {"input_tokens": 100, "output_tokens": 50}}\n',
    ]

    mock_proc.stdout = MockAsyncIterator(output_lines)
    mock_proc.stderr = MockAsyncIterator([])
    mock_proc.wait = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        result = await run_claude_cli(
            prompt="Test prompt",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-result-field",
            timeout_seconds=60
        )

    assert result.success is True
    assert result.cost_usd == 0.05
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    
    chunks = []
    while not output_queue.empty():
        chunk = await output_queue.get()
        if chunk is not None:
            chunks.append(chunk)
    
    content_chunks = [chunk for chunk in chunks if not chunk.startswith("[CLI] Process started")]
    
    assert "Processing task" in content_chunks
    assert "Task completed successfully" in content_chunks
    assert "Task completed successfully" in result.output


async def test_cli_runner_tool_result_no_truncation():
    import json
    
    output_queue = asyncio.Queue()

    mock_proc = AsyncMock()
    mock_proc.returncode = 0

    large_tool_result = "A" * 3000

    tool_result_message = {
        "type": "user",
        "message": {
            "content": [{
                "type": "tool_result",
                "content": large_tool_result,
                "is_error": False
            }]
        }
    }
    
    output_lines = [
        b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "I will read the file"}]}}\n',
        b'{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "large_file.txt"}}]}}\n',
        json.dumps(tool_result_message).encode() + b'\n',
        b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "File read successfully"}]}}\n',
        b'{"type": "result", "cost_usd": 0.05, "usage": {"input_tokens": 100, "output_tokens": 50}}\n',
    ]

    mock_proc.stdout = MockAsyncIterator(output_lines)
    mock_proc.stderr = MockAsyncIterator([])
    mock_proc.wait = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        result = await run_claude_cli(
            prompt="Read a large file",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-large-tool-result",
            timeout_seconds=60
        )

    assert result.success is True

    chunks = []
    while not output_queue.empty():
        chunk = await output_queue.get()
        if chunk is not None:
            chunks.append(chunk)

    full_output = "".join(chunks)

    assert "[TOOL RESULT]" in full_output
    assert large_tool_result in full_output
    assert len(large_tool_result) == 3000
    
    assert large_tool_result in result.output
    
    assert hasattr(result, 'clean_output')
    assert "[TOOL RESULT]" not in result.clean_output
    assert large_tool_result not in result.clean_output
    
    assert "I will read the file" in result.clean_output
    assert "File read successfully" in result.clean_output


async def test_cli_runner_tool_error_no_truncation():
    import json
    
    output_queue = asyncio.Queue()

    mock_proc = AsyncMock()
    mock_proc.returncode = 0

    large_error_result = "Error: " + "B" * 3000

    tool_error_message = {
        "type": "user",
        "message": {
            "content": [{
                "type": "tool_result",
                "content": large_error_result,
                "is_error": True
            }]
        }
    }
    
    output_lines = [
        b'{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "missing.txt"}}]}}\n',
        json.dumps(tool_error_message).encode() + b'\n',
        b'{"type": "result", "cost_usd": 0.05, "usage": {"input_tokens": 100, "output_tokens": 50}}\n',
    ]

    mock_proc.stdout = MockAsyncIterator(output_lines)
    mock_proc.stderr = MockAsyncIterator([])
    mock_proc.wait = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        result = await run_claude_cli(
            prompt="Read a file",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-large-tool-error",
            timeout_seconds=60
        )

    assert result.success is True

    chunks = []
    while not output_queue.empty():
        chunk = await output_queue.get()
        if chunk is not None:
            chunks.append(chunk)

    full_output = "".join(chunks)

    assert "[TOOL ERROR]" in full_output
    assert large_error_result in full_output
    assert len(large_error_result) == 3007
    
    assert large_error_result in result.output
    
    assert "[TOOL ERROR]" not in result.clean_output
    assert large_error_result not in result.clean_output
