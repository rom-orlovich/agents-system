import pytest
import asyncio
from pathlib import Path
import json
import tempfile
from core.streaming_logger import StreamingLogger


@pytest.fixture
def temp_logs_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def streaming_logger(temp_logs_dir):
    return StreamingLogger("test-task-123", temp_logs_dir)


@pytest.mark.asyncio
async def test_streaming_logger_logs_progress(streaming_logger, temp_logs_dir):
    await streaming_logger.log_progress(
        stage="execution", message="Test progress", success=True
    )

    stream_file = temp_logs_dir / "test-task-123" / "stream.jsonl"
    assert stream_file.exists()

    with open(stream_file) as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event_type"] == "progress"
    assert log_entry["stage"] == "execution"
    assert log_entry["message"] == "Test progress"
    assert log_entry["success"] is True


@pytest.mark.asyncio
async def test_streaming_logger_logs_error(streaming_logger, temp_logs_dir):
    await streaming_logger.log_error(error="Test error", context_key="context_value")

    stream_file = temp_logs_dir / "test-task-123" / "stream.jsonl"

    with open(stream_file) as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event_type"] == "error"
    assert log_entry["error"] == "Test error"
    assert log_entry["context_key"] == "context_value"


@pytest.mark.asyncio
async def test_streaming_logger_logs_cli_output(streaming_logger, temp_logs_dir):
    await streaming_logger.log_cli_output(line="Output line", stream="stdout")

    stream_file = temp_logs_dir / "test-task-123" / "stream.jsonl"

    with open(stream_file) as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event_type"] == "cli_output"
    assert log_entry["line"] == "Output line"
    assert log_entry["stream"] == "stdout"


@pytest.mark.asyncio
async def test_streaming_logger_logs_mcp_call(streaming_logger, temp_logs_dir):
    await streaming_logger.log_mcp_call(
        tool_name="test_tool", arguments={"key": "value", "count": 42}
    )

    stream_file = temp_logs_dir / "test-task-123" / "stream.jsonl"

    with open(stream_file) as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event_type"] == "mcp_call"
    assert log_entry["tool_name"] == "test_tool"
    assert log_entry["arguments"]["key"] == "value"
    assert log_entry["arguments"]["count"] == 42


@pytest.mark.asyncio
async def test_streaming_logger_logs_mcp_result(streaming_logger, temp_logs_dir):
    await streaming_logger.log_mcp_result(
        tool_name="test_tool", success=True, result="Test result"
    )

    stream_file = temp_logs_dir / "test-task-123" / "stream.jsonl"

    with open(stream_file) as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event_type"] == "mcp_result"
    assert log_entry["tool_name"] == "test_tool"
    assert log_entry["success"] is True
    assert log_entry["result"] == "Test result"


@pytest.mark.asyncio
async def test_streaming_logger_logs_completion(streaming_logger, temp_logs_dir):
    await streaming_logger.log_completion(
        success=True, result="Final result", error=None
    )

    stream_file = temp_logs_dir / "test-task-123" / "stream.jsonl"

    with open(stream_file) as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event_type"] == "completion"
    assert log_entry["success"] is True
    assert log_entry["result"] == "Final result"


@pytest.mark.asyncio
async def test_streaming_logger_stream_iteration(streaming_logger):
    await streaming_logger.log_progress(stage="test", message="Message 1")
    await streaming_logger.log_progress(stage="test", message="Message 2")
    await streaming_logger.close()

    messages = []
    async for entry in streaming_logger.stream():
        messages.append(entry["message"])

    assert "Message 1" in messages
    assert "Message 2" in messages


@pytest.mark.asyncio
async def test_streaming_logger_does_not_log_after_close(
    streaming_logger, temp_logs_dir
):
    await streaming_logger.close()
    await streaming_logger.log_progress(stage="test", message="Should not log")

    stream_file = temp_logs_dir / "test-task-123" / "stream.jsonl"

    with open(stream_file) as f:
        lines = f.readlines()

    assert len(lines) == 0
