from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from adapters.queue.redis_adapter import (
    RedisQueueAdapter,
    RedisConnectionError,
)
from ports.queue import TaskQueueMessage, TaskPriority


@pytest.fixture
def redis_url() -> str:
    return "redis://localhost:6379/0"


@pytest.fixture
def sample_message() -> TaskQueueMessage:
    return TaskQueueMessage(
        task_id="task-123",
        installation_id="inst-456",
        provider="github",
        input_message="Test task",
        priority=TaskPriority.NORMAL,
        source_metadata={"repo": "test/repo"},
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_redis_client():
    client = AsyncMock()
    client.ping = AsyncMock()
    client.zadd = AsyncMock()
    client.bzpopmin = AsyncMock()
    client.zcard = AsyncMock(return_value=5)
    client.close = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_enqueue_success(
    redis_url: str,
    sample_message: TaskQueueMessage,
    mock_redis_client: AsyncMock,
):
    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch(
        "adapters.queue.redis_adapter.redis.from_url",
        side_effect=mock_from_url,
    ):
        adapter = RedisQueueAdapter(redis_url)
        await adapter.enqueue(sample_message)

        mock_redis_client.zadd.assert_called_once()
        call_args = mock_redis_client.zadd.call_args
        assert call_args[0][0] == "agent:tasks"


@pytest.mark.asyncio
async def test_dequeue_success(
    redis_url: str,
    sample_message: TaskQueueMessage,
    mock_redis_client: AsyncMock,
):
    message_json = sample_message.model_dump_json()
    mock_redis_client.bzpopmin.return_value = (
        "agent:tasks",
        message_json,
        2.0,
    )

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch(
        "adapters.queue.redis_adapter.redis.from_url",
        side_effect=mock_from_url,
    ):
        adapter = RedisQueueAdapter(redis_url)
        result = await adapter.dequeue(timeout_seconds=5.0)

        assert result is not None
        assert result.task_id == sample_message.task_id
        assert result.priority == sample_message.priority


@pytest.mark.asyncio
async def test_dequeue_timeout(
    redis_url: str, mock_redis_client: AsyncMock
):
    mock_redis_client.bzpopmin.return_value = None

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch(
        "adapters.queue.redis_adapter.redis.from_url",
        side_effect=mock_from_url,
    ):
        adapter = RedisQueueAdapter(redis_url)
        result = await adapter.dequeue(timeout_seconds=1.0)

        assert result is None


@pytest.mark.asyncio
async def test_get_queue_size(redis_url: str, mock_redis_client: AsyncMock):
    mock_redis_client.zcard.return_value = 42

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch(
        "adapters.queue.redis_adapter.redis.from_url",
        side_effect=mock_from_url,
    ):
        adapter = RedisQueueAdapter(redis_url)
        size = await adapter.get_queue_size()

        assert size == 42


@pytest.mark.asyncio
async def test_connection_retry(redis_url: str, mock_redis_client: AsyncMock):
    mock_redis_client.ping.side_effect = [
        Exception("Connection failed"),
        Exception("Connection failed"),
        None,
    ]

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch(
        "adapters.queue.redis_adapter.redis.from_url",
        side_effect=mock_from_url,
    ):
        adapter = RedisQueueAdapter(redis_url)
        client = await adapter._ensure_connected()

        assert client is not None
        assert mock_redis_client.ping.call_count == 3


@pytest.mark.asyncio
async def test_connection_failure(redis_url: str, mock_redis_client: AsyncMock):
    mock_redis_client.ping.side_effect = Exception("Connection failed")

    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch(
        "adapters.queue.redis_adapter.redis.from_url",
        side_effect=mock_from_url,
    ):
        adapter = RedisQueueAdapter(redis_url)

        with pytest.raises(RedisConnectionError):
            await adapter._ensure_connected()


@pytest.mark.asyncio
async def test_close(redis_url: str, mock_redis_client: AsyncMock):
    async def mock_from_url(*args, **kwargs):
        return mock_redis_client

    with patch(
        "adapters.queue.redis_adapter.redis.from_url",
        side_effect=mock_from_url,
    ):
        adapter = RedisQueueAdapter(redis_url)
        await adapter._ensure_connected()
        await adapter.close()

        mock_redis_client.close.assert_called_once()
