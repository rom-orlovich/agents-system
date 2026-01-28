"""Pytest fixtures for all tests."""

import os
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Set test database URL before importing main
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from main import app
from core.database.models import Base
from core.database import get_session
from shared import Task, TaskStatus, AgentType

pytest_plugins = [
    "tests.fixtures.cli_fixtures",
]


# Note: event_loop fixture removed - pytest-asyncio handles this automatically in auto mode


@pytest.fixture(scope="session")
async def db_engine():
    """Create test database engine (session-scoped for performance)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db(db_engine):
    """Create test database session for direct use in tests."""
    async_session_maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def db_session(db_engine):
    """Create test database session with automatic rollback."""
    async_session_maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
        # Rollback after test completes to ensure test isolation
        await session.rollback()


@pytest.fixture(scope="session")
def redis_mock():
    """Mock Redis client (session-scoped for performance)."""
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
    
    # Subagent management
    mock.add_active_subagent = AsyncMock()
    mock.remove_active_subagent = AsyncMock()
    mock.get_active_subagents = AsyncMock(return_value=[])
    mock.get_active_subagent_count = AsyncMock(return_value=0)
    mock.get_subagent_status = AsyncMock(return_value=None)
    mock.update_subagent_status = AsyncMock()
    mock.append_subagent_output = AsyncMock()
    mock.get_subagent_output = AsyncMock(return_value="")
    
    # Parallel execution
    mock.create_parallel_group = AsyncMock()
    mock.get_parallel_group_agents = AsyncMock(return_value=[])
    mock.set_parallel_result = AsyncMock()
    mock.get_parallel_results = AsyncMock(return_value={})
    mock.get_parallel_status = AsyncMock(return_value={"status": "running", "total": "0", "completed": "0"})
    
    # Machine management
    mock.register_machine = AsyncMock()
    mock.update_machine_heartbeat = AsyncMock()
    mock.set_machine_status = AsyncMock()
    mock.get_machine_status = AsyncMock(return_value={})
    mock.get_active_machines = AsyncMock(return_value=[])
    mock.unregister_machine = AsyncMock()
    mock.set_machine_metrics = AsyncMock()
    mock.get_machine_metrics = AsyncMock(return_value={})
    
    # Container management
    mock.set_container_resources = AsyncMock()
    mock.get_container_resources = AsyncMock(return_value={})
    
    return mock


@pytest.fixture
async def client(db_session, redis_mock):
    """Create async HTTP client for API tests with mocked dependencies."""
    from httpx import ASGITransport

    # Override dependencies
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    # Mock Redis in all modules
    # Note: All modules import from core.database.redis_client, so we patch that
    with patch('main.redis_client', redis_mock):
        with patch('core.database.redis_client.redis_client', redis_mock):
            with patch('core.webhook_engine.redis_client', redis_mock):
                with patch('api.dashboard.redis_client', redis_mock):
                    with patch('api.subagents.redis_client', redis_mock):
                        with patch('api.container.redis_client', redis_mock):
                            with patch('api.accounts.redis_client', redis_mock):
                                with patch('api.sessions.redis_client', redis_mock):
                                    with patch('api.websocket.redis_client', redis_mock):
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
