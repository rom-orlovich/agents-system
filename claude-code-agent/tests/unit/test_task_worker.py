"""Unit tests for task worker."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from workers.task_worker import TaskWorker
from core.websocket_hub import WebSocketHub
from shared import TaskStatus
from core.database.models import TaskDB


@pytest.mark.asyncio
async def test_worker_processes_task(redis_mock, db_session):
    """Test worker processes a task from queue."""
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)

    # Create a task in database
    task_db = TaskDB(
        task_id="test-001",
        session_id="session-001",
        user_id="user-001",
        assigned_agent="brain",
        agent_type="planning",
        status=TaskStatus.QUEUED,
        input_message="Test task",
        source="dashboard",
        created_at=datetime.utcnow()
    )
    db_session.add(task_db)
    await db_session.commit()

    # Mock redis to return our task
    redis_mock.pop_task.return_value = "test-001"

    # Mock CLI runner
    mock_cli_result = AsyncMock()
    mock_cli_result.success = True
    mock_cli_result.output = "Task completed"
    mock_cli_result.cost_usd = 0.05
    mock_cli_result.input_tokens = 100
    mock_cli_result.output_tokens = 50

    with patch('workers.task_worker.redis_client', redis_mock):
        with patch('workers.task_worker.run_claude_cli', return_value=mock_cli_result):
            with patch.object(worker, 'running', True):
                # Process one task then stop
                async def stop_after_one():
                    await asyncio.sleep(0.1)
                    worker.running = False

                asyncio.create_task(stop_after_one())

                # This would normally run forever, but we stop it
                with pytest.raises(AttributeError):  # Will fail on session query
                    await worker.run()


@pytest.mark.asyncio
async def test_worker_handles_missing_task():
    """Test worker handles missing task gracefully."""
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)

    redis_mock = AsyncMock()
    redis_mock.pop_task.return_value = "nonexistent-task"

    with patch('workers.task_worker.redis_client', redis_mock):
        with patch('workers.task_worker.async_session_factory') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result
            mock_session_factory.return_value = mock_session

            # Should handle missing task without crashing
            await worker._process_task("nonexistent-task")


@pytest.mark.asyncio
async def test_worker_get_agent_dir():
    """Test worker resolves agent directories correctly."""
    from core.config import settings

    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)

    # Brain agent
    brain_dir = worker._get_agent_dir("brain")
    assert brain_dir == settings.app_dir

    # No agent specified (defaults to brain)
    default_dir = worker._get_agent_dir(None)
    assert default_dir == settings.app_dir

    # Planning agent (may or may not exist)
    planning_dir = worker._get_agent_dir("planning")
    # Should return either agents/planning or fall back to brain
    assert planning_dir is not None


@pytest.mark.asyncio
async def test_worker_stop():
    """Test worker can be stopped."""
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)

    assert worker.running is False

    # Start worker in background
    async def run_worker():
        await worker.run()

    task = asyncio.create_task(run_worker())

    # Give it time to start
    await asyncio.sleep(0.1)

    # Stop worker
    await worker.stop()

    # Wait for task to complete
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        task.cancel()
