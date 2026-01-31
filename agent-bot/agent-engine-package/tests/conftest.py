import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.lpush = AsyncMock()
    redis.brpop = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.append = AsyncMock()
    redis.delete = AsyncMock()
    redis.llen = AsyncMock(return_value=0)
    redis.close = AsyncMock()
    return redis


@pytest.fixture
def mock_process() -> MagicMock:
    process = MagicMock()
    process.pid = 12345
    process.returncode = 0
    process.stdout = AsyncMock()
    process.stderr = AsyncMock()
    process.wait = AsyncMock(return_value=0)
    process.kill = MagicMock()
    return process


@pytest.fixture
def sample_task_data() -> dict[str, str]:
    return {
        "task_id": "task-test-123",
        "prompt": "Test prompt",
        "agent_type": "brain",
        "source": "test",
    }
