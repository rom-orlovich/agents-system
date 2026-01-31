import pytest
from unittest.mock import AsyncMock
from agent_engine.core.queue_manager import QueueManager, TaskStatus


class TestTaskStatus:
    def test_pending_status(self) -> None:
        assert TaskStatus.PENDING.value == "pending"

    def test_running_status(self) -> None:
        assert TaskStatus.RUNNING.value == "running"

    def test_completed_status(self) -> None:
        assert TaskStatus.COMPLETED.value == "completed"

    def test_failed_status(self) -> None:
        assert TaskStatus.FAILED.value == "failed"


class TestQueueManager:
    @pytest.mark.asyncio
    async def test_push_task(self, mock_redis: AsyncMock) -> None:
        manager = QueueManager(redis_client=mock_redis)
        await manager.push_task("task-123")
        mock_redis.lpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_pop_task_returns_task(self, mock_redis: AsyncMock) -> None:
        mock_redis.brpop.return_value = (b"tasks", b"task-123")
        manager = QueueManager(redis_client=mock_redis)
        task_id = await manager.pop_task(timeout=5)
        assert task_id == "task-123"

    @pytest.mark.asyncio
    async def test_pop_task_returns_none_on_timeout(self, mock_redis: AsyncMock) -> None:
        mock_redis.brpop.return_value = None
        manager = QueueManager(redis_client=mock_redis)
        task_id = await manager.pop_task(timeout=1)
        assert task_id is None

    @pytest.mark.asyncio
    async def test_set_task_status(self, mock_redis: AsyncMock) -> None:
        manager = QueueManager(redis_client=mock_redis)
        await manager.set_task_status("task-123", TaskStatus.RUNNING)
        mock_redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_get_task_status(self, mock_redis: AsyncMock) -> None:
        mock_redis.get.return_value = b"running"
        manager = QueueManager(redis_client=mock_redis)
        status = await manager.get_task_status("task-123")
        assert status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self, mock_redis: AsyncMock) -> None:
        mock_redis.get.return_value = None
        manager = QueueManager(redis_client=mock_redis)
        status = await manager.get_task_status("task-nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_append_output(self, mock_redis: AsyncMock) -> None:
        manager = QueueManager(redis_client=mock_redis)
        await manager.append_output("task-123", "chunk of output")
        mock_redis.append.assert_called()

    @pytest.mark.asyncio
    async def test_get_output(self, mock_redis: AsyncMock) -> None:
        mock_redis.get.return_value = b"accumulated output"
        manager = QueueManager(redis_client=mock_redis)
        output = await manager.get_output("task-123")
        assert output == "accumulated output"

    @pytest.mark.asyncio
    async def test_get_queue_length(self, mock_redis: AsyncMock) -> None:
        mock_redis.llen.return_value = 5
        manager = QueueManager(redis_client=mock_redis)
        length = await manager.get_queue_length()
        assert length == 5

    @pytest.mark.asyncio
    async def test_close(self, mock_redis: AsyncMock) -> None:
        manager = QueueManager(redis_client=mock_redis)
        await manager.close()
        mock_redis.close.assert_called_once()
