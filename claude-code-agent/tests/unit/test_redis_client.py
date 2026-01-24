"""Unit tests for Redis client."""

import pytest
import json
from unittest.mock import AsyncMock, patch

from core.database.redis_client import RedisClient
async def test_redis_connect():
    """Test Redis connection."""
    client = RedisClient()

    with patch('redis.asyncio.from_url') as mock_from_url:
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis

        await client.connect()

        mock_from_url.assert_called_once()
        assert client._client is mock_redis
async def test_redis_disconnect():
    """Test Redis disconnection."""
    client = RedisClient()
    client._client = AsyncMock()

    await client.disconnect()

    client._client.close.assert_called_once()
async def test_push_task():
    """Test pushing task to queue."""
    client = RedisClient()
    client._client = AsyncMock()

    await client.push_task("test-001")

    client._client.rpush.assert_called_once_with("task_queue", "test-001")
async def test_push_task_not_connected():
    """Test pushing task when not connected raises error."""
    client = RedisClient()

    with pytest.raises(RuntimeError, match="Redis not connected"):
        await client.push_task("test-001")
async def test_pop_task():
    """Test popping task from queue."""
    client = RedisClient()
    client._client = AsyncMock()
    client._client.blpop.return_value = ("task_queue", "test-001")

    task_id = await client.pop_task(timeout=5)

    assert task_id == "test-001"
    client._client.blpop.assert_called_once_with("task_queue", timeout=5)
async def test_pop_task_empty_queue():
    """Test popping from empty queue returns None."""
    client = RedisClient()
    client._client = AsyncMock()
    client._client.blpop.return_value = None

    task_id = await client.pop_task(timeout=5)

    assert task_id is None
async def test_pop_task_not_connected():
    """Test popping task when not connected raises error."""
    client = RedisClient()

    with pytest.raises(RuntimeError, match="Redis not connected"):
        await client.pop_task()
async def test_set_task_status():
    """Test setting task status."""
    client = RedisClient()
    client._client = AsyncMock()

    await client.set_task_status("test-001", "running")

    client._client.set.assert_called_once_with(
        "task:test-001:status",
        "running",
        ex=3600
    )
async def test_get_task_status():
    """Test getting task status."""
    client = RedisClient()
    client._client = AsyncMock()
    client._client.get.return_value = "completed"

    status = await client.get_task_status("test-001")

    assert status == "completed"
    client._client.get.assert_called_once_with("task:test-001:status")
async def test_set_task_pid():
    """Test setting task PID."""
    client = RedisClient()
    client._client = AsyncMock()

    await client.set_task_pid("test-001", 12345)

    client._client.set.assert_called_once_with(
        "task:test-001:pid",
        "12345",
        ex=3600
    )
async def test_get_task_pid():
    """Test getting task PID."""
    client = RedisClient()
    client._client = AsyncMock()
    client._client.get.return_value = "12345"

    pid = await client.get_task_pid("test-001")

    assert pid == 12345
async def test_get_task_pid_not_found():
    """Test getting nonexistent PID returns None."""
    client = RedisClient()
    client._client = AsyncMock()
    client._client.get.return_value = None

    pid = await client.get_task_pid("test-001")

    assert pid is None
async def test_append_output():
    """Test appending output chunk."""
    client = RedisClient()
    client._client = AsyncMock()

    await client.append_output("test-001", "Hello World")

    client._client.append.assert_called_once_with(
        "task:test-001:output",
        "Hello World"
    )
    client._client.expire.assert_called_once_with(
        "task:test-001:output",
        3600
    )
async def test_get_output():
    """Test getting accumulated output."""
    client = RedisClient()
    client._client = AsyncMock()
    client._client.get.return_value = "Hello World"

    output = await client.get_output("test-001")

    assert output == "Hello World"
async def test_add_session_task():
    """Test adding task to session."""
    client = RedisClient()
    client._client = AsyncMock()

    await client.add_session_task("session-001", "test-001")

    client._client.sadd.assert_called_once_with(
        "session:session-001:tasks",
        "test-001"
    )
    client._client.expire.assert_called_once_with(
        "session:session-001:tasks",
        86400
    )
async def test_get_session_tasks():
    """Test getting session tasks."""
    client = RedisClient()
    client._client = AsyncMock()
    client._client.smembers.return_value = {"test-001", "test-002", "test-003"}

    tasks = await client.get_session_tasks("session-001")

    assert len(tasks) == 3
    assert "test-001" in tasks
    assert "test-002" in tasks
    assert "test-003" in tasks
async def test_set_json():
    """Test setting JSON data."""
    client = RedisClient()
    client._client = AsyncMock()

    data = {"foo": "bar", "count": 42}
    await client.set_json("test-key", data, ex=300)

    expected_json = json.dumps(data)
    client._client.set.assert_called_once_with(
        "test-key",
        expected_json,
        ex=300
    )
async def test_get_json():
    """Test getting JSON data."""
    client = RedisClient()
    client._client = AsyncMock()

    data = {"foo": "bar", "count": 42}
    client._client.get.return_value = json.dumps(data)

    result = await client.get_json("test-key")

    assert result == data
async def test_get_json_not_found():
    """Test getting nonexistent JSON returns None."""
    client = RedisClient()
    client._client = AsyncMock()
    client._client.get.return_value = None

    result = await client.get_json("test-key")

    assert result is None
async def test_delete():
    """Test deleting key."""
    client = RedisClient()
    client._client = AsyncMock()

    await client.delete("test-key")

    client._client.delete.assert_called_once_with("test-key")
async def test_queue_length():
    """Test getting queue length."""
    client = RedisClient()
    client._client = AsyncMock()
    client._client.llen.return_value = 5

    length = await client.queue_length()

    assert length == 5
    client._client.llen.assert_called_once_with("task_queue")
async def test_queue_length_not_connected():
    """Test queue length when not connected raises error."""
    client = RedisClient()

    with pytest.raises(RuntimeError, match="Redis not connected"):
        await client.queue_length()
