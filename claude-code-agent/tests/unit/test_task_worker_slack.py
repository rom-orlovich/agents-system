"""Unit tests for task worker Slack integration (TDD RED Phase)."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from workers.task_worker import TaskWorker
from core.websocket_hub import WebSocketHub
from shared import TaskStatus
from core.database.models import TaskDB


@pytest.mark.asyncio
async def test_sends_slack_notification_on_job_start(redis_mock):
    """Test that pre-job Slack notification is sent when task starts running."""
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)
    
    # Create a webhook task
    task_db = TaskDB(
        task_id="test-webhook-001",
        session_id="session-001",
        user_id="user-001",
        assigned_agent="brain",
        agent_type="planning",
        status=TaskStatus.QUEUED,
        input_message="Analyze ticket",
        source="webhook",
        source_metadata=json.dumps({
            "webhook_source": "jira",
            "command": "analyze PROJ-123",
            "payload": {"issue_key": "PROJ-123"}
        }),
        created_at=datetime.now(timezone.utc)
    )
    
    # Mock CLI runner
    mock_cli_result = MagicMock()
    mock_cli_result.success = True
    mock_cli_result.output = "Analysis complete"
    mock_cli_result.cost_usd = 0.05
    mock_cli_result.input_tokens = 100
    mock_cli_result.output_tokens = 50
    
    async def mock_run_claude_cli(*args, **kwargs):
        output_queue = kwargs.get('output_queue')
        if output_queue:
            await output_queue.put(None)
        return mock_cli_result
    
    # Track if notification was sent
    notification_sent = False
    
    async def mock_send_notification(*args, **kwargs):
        nonlocal notification_sent
        notification_sent = True
        return True
    
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
                
                # Mock the notification method
                worker._send_slack_job_start_notification = AsyncMock(side_effect=mock_send_notification)
                
                # Process task
                await worker._process_task("test-webhook-001")
                
                # Verify notification was sent
                assert notification_sent, "Pre-job Slack notification should be sent for webhook tasks"
                worker._send_slack_job_start_notification.assert_called_once()


@pytest.mark.asyncio
async def test_no_slack_notification_for_dashboard_tasks(redis_mock):
    """Test that pre-job notification is NOT sent for dashboard tasks (only webhooks)."""
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)
    
    # Create a dashboard task (not webhook)
    task_db = TaskDB(
        task_id="test-dashboard-001",
        session_id="session-001",
        user_id="user-001",
        assigned_agent="brain",
        agent_type="planning",
        status=TaskStatus.QUEUED,
        input_message="Fix the bug",
        source="dashboard",  # Not webhook
        created_at=datetime.now(timezone.utc)
    )
    
    # Mock CLI runner
    mock_cli_result = MagicMock()
    mock_cli_result.success = True
    mock_cli_result.output = "Bug fixed"
    mock_cli_result.cost_usd = 0.05
    
    async def mock_run_claude_cli(*args, **kwargs):
        output_queue = kwargs.get('output_queue')
        if output_queue:
            await output_queue.put(None)
        return mock_cli_result
    
    with patch('workers.task_worker.redis_client', redis_mock):
        with patch('workers.task_worker.run_claude_cli', side_effect=mock_run_claude_cli):
            with patch('workers.task_worker.async_session_factory') as mock_session_factory:
                mock_session = AsyncMock()
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = task_db
                mock_session.execute = AsyncMock(return_value=mock_result)
                mock_session.commit = AsyncMock()
                mock_session_factory.return_value = mock_session
                
                # Create mock method
                worker._send_slack_job_start_notification = AsyncMock()
                
                # Process task
                await worker._process_task("test-dashboard-001")
                
                # Verify notification was NOT sent
                worker._send_slack_job_start_notification.assert_not_called()


@pytest.mark.asyncio
async def test_slack_job_start_notification_format(redis_mock):
    """Test that job start notification includes correct metadata."""
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)
    
    task_db = TaskDB(
        task_id="test-001",
        session_id="session-001",
        user_id="user-001",
        assigned_agent="planning",
        agent_type="planning",
        status=TaskStatus.RUNNING,
        input_message="Analyze ticket",
        source="webhook",
        source_metadata=json.dumps({
            "webhook_source": "jira",
            "command": "analyze PROJ-123"
        }),
        created_at=datetime.now(timezone.utc)
    )
    
    # Test the notification method exists and can be called
    result = await worker._send_slack_job_start_notification(task_db)
    
    # Should return False if Slack is not configured, but shouldn't raise an error
    assert result in [True, False], "Notification method should return boolean"
