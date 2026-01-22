"""Pytest fixtures for all tests."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from main import app
from core.database.models import Base
from core.database import get_session
from shared import Task, TaskStatus, AgentType

# Import CLI testing fixtures
from tests.fixtures.cli_fixtures import (
    fake_claude_cli,
    fake_cli_success,
    fake_cli_error,
    fake_cli_timeout,
    fake_cli_auth_error,
    fake_cli_malformed,
    fake_cli_streaming,
    real_claude_cli,
    cli_test_workspace,
    dry_run_mode,
    pytest_configure,
    pytest_collection_modifyitems,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create test database session."""
    async_session_maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def redis_mock():
    """Mock Redis client."""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.push_task = AsyncMock()
    mock.pop_task = AsyncMock(return_value=None)
    mock.queue_length = AsyncMock(return_value=0)
    mock.set_task_status = AsyncMock()
    mock.get_task_status = AsyncMock(return_value="queued")
    mock.append_output = AsyncMock()
    mock.get_output = AsyncMock(return_value="")
    mock.add_session_task = AsyncMock()
    mock.get_session_tasks = AsyncMock(return_value=[])
    return mock


@pytest.fixture
async def client(db_session, redis_mock):
    """Create async HTTP client for API tests with mocked dependencies."""
    from httpx import ASGITransport
    from core.database import redis_client

    # Override dependencies
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    # Mock Redis in all modules
    with patch('main.redis_client', redis_mock):
        with patch('core.database.redis_client.redis_client', redis_mock):
            with patch('api.dashboard.redis_client', redis_mock):
                with patch('api.webhooks.redis_client', redis_mock):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        yield client

    # Clean up
    app.dependency_overrides.clear()


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
