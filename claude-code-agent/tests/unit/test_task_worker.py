"""Unit tests for task worker."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from workers.task_worker import TaskWorker
from core.websocket_hub import WebSocketHub
from shared import TaskStatus
from core.database.models import TaskDB
async def test_worker_processes_task(redis_mock):
    """Test worker processes a task from queue."""
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)

    # Create a mock task
    task_db = TaskDB(
        task_id="test-001",
        session_id="session-001",
        user_id="user-001",
        assigned_agent="brain",
        agent_type="planning",
        status=TaskStatus.QUEUED,
        input_message="Test task",
        source="dashboard",
        created_at=datetime.now(timezone.utc)
    )

    # Mock redis to return our task
    redis_mock.pop_task.return_value = "test-001"

    # Mock CLI runner to complete immediately
    mock_cli_result = MagicMock()
    mock_cli_result.success = True
    mock_cli_result.output = "Task completed"
    mock_cli_result.cost_usd = 0.05
    mock_cli_result.input_tokens = 100
    mock_cli_result.output_tokens = 50

    # Mock the output queue to end immediately
    async def mock_run_claude_cli(*args, **kwargs):
        output_queue = kwargs.get('output_queue')
        if output_queue:
            await output_queue.put(None)  # Signal end of stream
        return mock_cli_result

    with patch('workers.task_worker.redis_client', redis_mock):
        with patch('workers.task_worker.run_claude_cli', side_effect=mock_run_claude_cli):
            with patch('workers.task_worker.async_session_factory') as mock_session_factory:
                # Mock database session
                mock_session = AsyncMock()
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = task_db
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_session.commit = AsyncMock()
                mock_session_factory.return_value = mock_session

                # Process one task
                await worker._process_task("test-001")

                # Verify task was processed
                assert task_db.status == TaskStatus.COMPLETED
                assert task_db.result == "Task completed"
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
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session_factory.return_value = mock_session

            # Should handle missing task without crashing
            await worker._process_task("nonexistent-task")
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
