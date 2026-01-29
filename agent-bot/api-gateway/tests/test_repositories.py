import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from storage.database import Base
from storage.models import Task, WebhookEvent, TaskResult, APICall
from storage.repositories import (
    TaskRepository,
    WebhookEventRepository,
    TaskResultRepository,
    APICallRepository,
)
from core.models import TaskStatus, WebhookProvider
from datetime import datetime, timezone


@pytest.fixture
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", echo=False, future=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session


@pytest.mark.asyncio
async def test_task_repository_create(async_session: AsyncSession):
    repo = TaskRepository(async_session)

    task = Task(
        task_id="task-123",
        session_id="session-456",
        user_id="user-789",
        input_message="test message",
        agent_type="planning",
        model="claude-3-opus",
        priority=0,
        status=TaskStatus.QUEUED,
        source_metadata={"provider": "github"},
    )

    created_task = await repo.create(task)
    await async_session.commit()

    assert created_task.id is not None
    assert created_task.task_id == "task-123"
    assert created_task.status == TaskStatus.QUEUED


@pytest.mark.asyncio
async def test_task_repository_get_by_task_id(async_session: AsyncSession):
    repo = TaskRepository(async_session)

    task = Task(
        task_id="task-123",
        session_id="session-456",
        user_id="user-789",
        input_message="test message",
        agent_type="planning",
        model="claude-3-opus",
    )

    await repo.create(task)
    await async_session.commit()

    retrieved_task = await repo.get_by_task_id("task-123")

    assert retrieved_task is not None
    assert retrieved_task.task_id == "task-123"
    assert retrieved_task.input_message == "test message"


@pytest.mark.asyncio
async def test_task_repository_update_status(async_session: AsyncSession):
    repo = TaskRepository(async_session)

    task = Task(
        task_id="task-123",
        session_id="session-456",
        user_id="user-789",
        input_message="test message",
        agent_type="planning",
        model="claude-3-opus",
        status=TaskStatus.QUEUED,
    )

    await repo.create(task)
    await async_session.commit()

    updated = await repo.update_status("task-123", TaskStatus.PROCESSING)
    await async_session.commit()

    assert updated is True

    retrieved_task = await repo.get_by_task_id("task-123")
    assert retrieved_task is not None
    assert retrieved_task.status == TaskStatus.PROCESSING


@pytest.mark.asyncio
async def test_webhook_event_repository_create(async_session: AsyncSession):
    repo = WebhookEventRepository(async_session)

    event = WebhookEvent(
        event_id="event-123",
        task_id="task-456",
        provider=WebhookProvider.GITHUB,
        payload={"action": "created"},
        headers={"X-GitHub-Event": "issues"},
        signature_valid=True,
        processed=False,
    )

    created_event = await repo.create(event)
    await async_session.commit()

    assert created_event.id is not None
    assert created_event.event_id == "event-123"
    assert created_event.provider == WebhookProvider.GITHUB


@pytest.mark.asyncio
async def test_webhook_event_repository_list_unprocessed(async_session: AsyncSession):
    repo = WebhookEventRepository(async_session)

    event1 = WebhookEvent(
        event_id="event-1",
        provider=WebhookProvider.GITHUB,
        payload={},
        headers={},
        processed=False,
    )

    event2 = WebhookEvent(
        event_id="event-2",
        provider=WebhookProvider.GITHUB,
        payload={},
        headers={},
        processed=True,
    )

    await repo.create(event1)
    await repo.create(event2)
    await async_session.commit()

    unprocessed = await repo.list_unprocessed()

    assert len(unprocessed) == 1
    assert unprocessed[0].event_id == "event-1"


@pytest.mark.asyncio
async def test_task_result_repository_create(async_session: AsyncSession):
    repo = TaskResultRepository(async_session)

    result = TaskResult(
        task_id="task-123",
        success=True,
        output="Task completed successfully",
        error=None,
        cost_usd=0.05,
        input_tokens=100,
        output_tokens=200,
        execution_time_seconds=5.5,
    )

    created_result = await repo.create(result)
    await async_session.commit()

    assert created_result.id is not None
    assert created_result.task_id == "task-123"
    assert created_result.success is True


@pytest.mark.asyncio
async def test_api_call_repository_list_by_task(async_session: AsyncSession):
    repo = APICallRepository(async_session)

    call1 = APICall(
        task_id="task-123",
        service="github",
        endpoint="/repos/owner/repo/issues/1/comments",
        method="POST",
        request_payload={"body": "comment"},
        response_status=200,
        response_payload={"id": 1},
        duration_ms=150.5,
        success=True,
    )

    call2 = APICall(
        task_id="task-123",
        service="github",
        endpoint="/repos/owner/repo/pulls/1",
        method="GET",
        request_payload=None,
        response_status=200,
        response_payload={"number": 1},
        duration_ms=100.2,
        success=True,
    )

    await repo.create(call1)
    await repo.create(call2)
    await async_session.commit()

    calls = await repo.list_by_task("task-123")

    assert len(calls) == 2
    assert calls[0].service == "github"
