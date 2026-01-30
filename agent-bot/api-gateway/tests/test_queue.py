import pytest
from queue.redis_queue import TaskQueue
from core.models import TaskQueueMessage
from datetime import datetime, timezone
import fakeredis.aioredis


@pytest.fixture
async def redis_queue():
    fake_redis = await fakeredis.aioredis.FakeRedis.from_url("redis://localhost")
    queue = TaskQueue(redis_url="redis://localhost")
    queue.redis_client = fake_redis
    yield queue
    await queue.disconnect()


@pytest.mark.asyncio
async def test_enqueue_task(redis_queue: TaskQueue):
    task = TaskQueueMessage(
        task_id="task-123",
        session_id="session-456",
        user_id="user-789",
        input_message="analyze this issue",
        agent_type="planning",
        model="claude-3-opus",
        priority=0,
    )

    result = await redis_queue.enqueue(task, priority=0)

    assert result["task_id"] == "task-123"
    assert result["queue"] == "tasks"
    assert result["priority"] == 0

    queue_length = await redis_queue.get_queue_length()
    assert queue_length == 1


@pytest.mark.asyncio
async def test_dequeue_task(redis_queue: TaskQueue):
    task = TaskQueueMessage(
        task_id="task-123",
        session_id="session-456",
        user_id="user-789",
        input_message="analyze this issue",
        agent_type="planning",
        model="claude-3-opus",
    )

    await redis_queue.enqueue(task)

    dequeued_task = await redis_queue.dequeue(worker_id="worker-1")

    assert dequeued_task is not None
    assert dequeued_task.task_id == "task-123"
    assert dequeued_task.input_message == "analyze this issue"

    queue_length = await redis_queue.get_queue_length()
    assert queue_length == 0


@pytest.mark.asyncio
async def test_dequeue_empty_queue_returns_none(redis_queue: TaskQueue):
    dequeued_task = await redis_queue.dequeue(worker_id="worker-1")
    assert dequeued_task is None


@pytest.mark.asyncio
async def test_priority_queue_dequeues_highest_priority_first(redis_queue: TaskQueue):
    low_priority_task = TaskQueueMessage(
        task_id="task-low",
        session_id="session-1",
        user_id="user-1",
        input_message="low priority",
        agent_type="planning",
        model="claude-3-opus",
    )

    high_priority_task = TaskQueueMessage(
        task_id="task-high",
        session_id="session-2",
        user_id="user-2",
        input_message="high priority",
        agent_type="planning",
        model="claude-3-opus",
    )

    await redis_queue.enqueue(low_priority_task, priority=10)
    await redis_queue.enqueue(high_priority_task, priority=1)

    first_task = await redis_queue.dequeue(worker_id="worker-1")
    assert first_task is not None
    assert first_task.task_id == "task-high"

    second_task = await redis_queue.dequeue(worker_id="worker-1")
    assert second_task is not None
    assert second_task.task_id == "task-low"


@pytest.mark.asyncio
async def test_peek_tasks(redis_queue: TaskQueue):
    task1 = TaskQueueMessage(
        task_id="task-1",
        session_id="session-1",
        user_id="user-1",
        input_message="first task",
        agent_type="planning",
        model="claude-3-opus",
    )

    task2 = TaskQueueMessage(
        task_id="task-2",
        session_id="session-2",
        user_id="user-2",
        input_message="second task",
        agent_type="planning",
        model="claude-3-opus",
    )

    await redis_queue.enqueue(task1)
    await redis_queue.enqueue(task2)

    peeked_tasks = await redis_queue.peek(count=2)

    assert len(peeked_tasks) == 2
    assert peeked_tasks[0].task_id == "task-1"
    assert peeked_tasks[1].task_id == "task-2"

    queue_length = await redis_queue.get_queue_length()
    assert queue_length == 2
