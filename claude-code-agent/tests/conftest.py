"""Pytest fixtures for all tests."""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from main import app
from core.database.models import Base
from shared import Task, TaskStatus, AgentType


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """Create async HTTP client for API tests."""
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def db_session():
    """Create test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sample_task():
    """Create sample task for testing."""
    return Task(
        task_id="test-001",
        session_id="session-001",
        user_id="user-001",
        input_message="Fix the bug",
        status=TaskStatus.QUEUED,
        agent_type=AgentType.PLANNING,
    )


@pytest.fixture
def sample_task_dict():
    """Create sample task as dict."""
    return {
        "task_id": "test-001",
        "session_id": "session-001",
        "user_id": "user-001",
        "input_message": "Fix the bug",
        "status": "queued",
        "agent_type": "planning",
    }
