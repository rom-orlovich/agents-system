"""TDD tests for task worker completion handler invocation."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from workers.task_worker import TaskWorker
from core.websocket_hub import WebSocketHub
from shared import TaskStatus
from core.database.models import TaskDB


class TestTaskWorkerInvokeCompletionHandler:
    """Test task worker generic completion handler invocation."""
    
    @pytest.mark.asyncio
    async def test_invokes_registered_completion_handler_with_all_parameters(self):
        """
        Business Rule: Task worker must call completion handler with all required parameters.
        Behavior: Handler receives payload, message, success, cost_usd, task_id, command, result, error.
        """
        task_db = TaskDB(
            task_id="task-123",
            session_id="session-123",
            user_id="user-123",
            assigned_agent="brain",
            status=TaskStatus.COMPLETED,
            input_message="test",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "github",
                "payload": {"repository": {"owner": {"login": "test"}, "name": "repo"}},
                "completion_handler": "api.webhooks.github.routes.handle_github_task_completion",
                "command": "review pr"
            }),
            cost_usd=0.05
        )
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        with patch('api.webhooks.github.routes.handle_github_task_completion', new_callable=AsyncMock) as mock_handler:
            mock_handler.return_value = True
            
            result = await worker._invoke_completion_handler(
                task_db=task_db,
                message="Task completed successfully",
                success=True,
                result="Clean output",
                error=None
            )
            
            assert result is True
            mock_handler.assert_called_once_with(
                payload={"repository": {"owner": {"login": "test"}, "name": "repo"}},
                message="Task completed successfully",
                success=True,
                cost_usd=0.05,
                task_id="task-123",
                command="review pr",
                result="Clean output",
                error=None
            )
    
    @pytest.mark.asyncio
    async def test_invokes_handler_with_error_parameters_on_failure(self):
        """
        Business Rule: Task worker must pass error information to handler.
        Behavior: Handler receives error parameter when task fails.
        """
        task_db = TaskDB(
            task_id="task-456",
            session_id="session-456",
            user_id="user-456",
            assigned_agent="brain",
            status=TaskStatus.FAILED,
            input_message="test",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "jira",
                "payload": {"issue": {"key": "TEST-123"}},
                "completion_handler": "api.webhooks.jira.routes.handle_jira_task_completion",
                "command": "analyze ticket"
            }),
            cost_usd=0.0
        )
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        with patch('api.webhooks.jira.routes.handle_jira_task_completion', new_callable=AsyncMock) as mock_handler:
            mock_handler.return_value = False
            
            result = await worker._invoke_completion_handler(
                task_db=task_db,
                message="Task failed",
                success=False,
                result=None,
                error="Something went wrong"
            )
            
            assert result is False
            mock_handler.assert_called_once_with(
                payload={"issue": {"key": "TEST-123"}},
                message="Task failed",
                success=False,
                cost_usd=0.0,
                task_id="task-456",
                command="analyze ticket",
                result=None,
                error="Something went wrong"
            )
    
    @pytest.mark.asyncio
    async def test_returns_false_when_completion_handler_missing(self):
        """
        Business Rule: Task worker must handle missing completion handler gracefully.
        Behavior: Returns False and logs debug when handler path not found in metadata.
        """
        task_db = TaskDB(
            task_id="task-789",
            session_id="session-789",
            user_id="user-789",
            assigned_agent="brain",
            status=TaskStatus.COMPLETED,
            input_message="test",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "github",
                "payload": {"issue": {"number": 123}}
            }),
            cost_usd=0.0
        )
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        result = await worker._invoke_completion_handler(
            task_db=task_db,
            message="Test",
            success=True
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_returns_false_when_payload_missing(self):
        """
        Business Rule: Task worker must handle missing payload gracefully.
        Behavior: Returns False and logs debug when payload not found in metadata.
        """
        task_db = TaskDB(
            task_id="task-999",
            session_id="session-999",
            user_id="user-999",
            assigned_agent="brain",
            status=TaskStatus.COMPLETED,
            input_message="test",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "slack",
                "completion_handler": "api.webhooks.slack.routes.handle_slack_task_completion"
            }),
            cost_usd=0.0
        )
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        result = await worker._invoke_completion_handler(
            task_db=task_db,
            message="Test",
            success=True
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_handles_handler_exception_gracefully(self):
        """
        Business Rule: Task worker must handle handler exceptions without crashing.
        Behavior: Returns False and logs error when handler raises exception.
        """
        task_db = TaskDB(
            task_id="task-error",
            session_id="session-error",
            user_id="user-error",
            assigned_agent="brain",
            status=TaskStatus.COMPLETED,
            input_message="test",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "github",
                "payload": {"repository": {"name": "repo"}},
                "completion_handler": "api.webhooks.github.routes.handle_github_task_completion"
            }),
            cost_usd=0.0
        )
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        with patch('api.webhooks.github.routes.handle_github_task_completion', new_callable=AsyncMock) as mock_handler:
            mock_handler.side_effect = Exception("Handler failed")
            
            result = await worker._invoke_completion_handler(
                task_db=task_db,
                message="Test",
                success=True
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_handles_invalid_module_path_gracefully(self):
        """
        Business Rule: Task worker must handle invalid handler paths gracefully.
        Behavior: Returns False and logs error when module cannot be imported.
        """
        task_db = TaskDB(
            task_id="task-invalid",
            session_id="session-invalid",
            user_id="user-invalid",
            assigned_agent="brain",
            status=TaskStatus.COMPLETED,
            input_message="test",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "github",
                "payload": {"repository": {"name": "repo"}},
                "completion_handler": "nonexistent.module.handler"
            }),
            cost_usd=0.0
        )
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        result = await worker._invoke_completion_handler(
            task_db=task_db,
            message="Test",
            success=True
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_handles_empty_source_metadata(self):
        """
        Business Rule: Task worker must handle empty source_metadata gracefully.
        Behavior: Returns False when source_metadata is None or empty.
        """
        task_db = TaskDB(
            task_id="task-empty",
            session_id="session-empty",
            user_id="user-empty",
            assigned_agent="brain",
            status=TaskStatus.COMPLETED,
            input_message="test",
            source="webhook",
            source_metadata=None,
            cost_usd=0.0
        )
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        result = await worker._invoke_completion_handler(
            task_db=task_db,
            message="Test",
            success=True
        )
        
        assert result is False
