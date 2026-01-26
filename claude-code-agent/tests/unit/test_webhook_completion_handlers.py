"""Unit tests for webhook completion handler flow (TDD)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from core.database.models import TaskDB
from shared import TaskStatus


class TestWebhookCompletionHandlerFlow:
    """Test webhook completion handler registration and execution."""
    
    async def test_github_task_has_completion_handler_in_metadata(self):
        """
        Business Rule: GitHub tasks must have completion handler registered.
        Behavior: Task source_metadata contains completion_handler path.
        """
        from api.webhooks.github.utils import create_github_task
        from core.webhook_configs import GITHUB_WEBHOOK
        
        command = GITHUB_WEBHOOK.commands[0]
        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo", "full_name": "test/repo"},
            "issue": {"number": 123}
        }
        
        db_mock = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        db_mock.commit = AsyncMock()
        
        with patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock), \
             patch('api.webhooks.github.utils.create_webhook_conversation', new_callable=AsyncMock, return_value="conv-123"):
            
            task_id = await create_github_task(
                command, 
                payload, 
                db_mock,
                completion_handler="api.webhooks.github.routes.handle_github_task_completion"
            )
            
            call_args = db_mock.add.call_args_list
            task_db = None
            for call in call_args:
                arg = call[0][0]
                if isinstance(arg, TaskDB):
                    task_db = arg
                    break
            
            assert task_db is not None
            source_metadata = json.loads(task_db.source_metadata)
            assert "completion_handler" in source_metadata
            assert source_metadata["completion_handler"] == "api.webhooks.github.routes.handle_github_task_completion"
    
    async def test_jira_task_has_completion_handler_in_metadata(self):
        """
        Business Rule: Jira tasks must have completion handler registered.
        Behavior: Task source_metadata contains completion_handler path.
        """
        from api.webhooks.jira.utils import create_jira_task
        from core.webhook_configs import JIRA_WEBHOOK
        
        command = JIRA_WEBHOOK.commands[0]
        payload = {
            "issue": {"key": "TEST-123", "fields": {"summary": "Test"}}
        }
        
        db_mock = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        db_mock.commit = AsyncMock()
        
        with patch('api.webhooks.jira.utils.redis_client.push_task', new_callable=AsyncMock), \
             patch('api.webhooks.jira.utils.create_webhook_conversation', new_callable=AsyncMock, return_value="conv-123"):
            
            task_id = await create_jira_task(
                command, 
                payload, 
                db_mock,
                completion_handler="api.webhooks.jira.routes.handle_jira_task_completion"
            )
            
            call_args = db_mock.add.call_args_list
            task_db = None
            for call in call_args:
                arg = call[0][0]
                if isinstance(arg, TaskDB):
                    task_db = arg
                    break
            
            assert task_db is not None
            source_metadata = json.loads(task_db.source_metadata)
            assert "completion_handler" in source_metadata
            assert source_metadata["completion_handler"] == "api.webhooks.jira.routes.handle_jira_task_completion"
    
    async def test_slack_task_has_completion_handler_in_metadata(self):
        """
        Business Rule: Slack tasks must have completion handler registered.
        Behavior: Task source_metadata contains completion_handler path.
        """
        from api.webhooks.slack.utils import create_slack_task
        from core.webhook_configs import SLACK_WEBHOOK
        
        command = SLACK_WEBHOOK.commands[0]
        payload = {
            "event": {"channel": "C123", "text": "@agent help", "user": "U123"}
        }
        
        db_mock = AsyncMock()
        db_mock.add = MagicMock()
        db_mock.flush = AsyncMock()
        db_mock.commit = AsyncMock()
        
        with patch('api.webhooks.slack.utils.redis_client.push_task', new_callable=AsyncMock), \
             patch('api.webhooks.slack.utils.create_webhook_conversation', new_callable=AsyncMock, return_value="conv-123"):
            
            task_id = await create_slack_task(
                command, 
                payload, 
                db_mock,
                completion_handler="api.webhooks.slack.routes.handle_slack_task_completion"
            )
            
            call_args = db_mock.add.call_args_list
            task_db = None
            for call in call_args:
                arg = call[0][0]
                if isinstance(arg, TaskDB):
                    task_db = arg
                    break
            
            assert task_db is not None
            source_metadata = json.loads(task_db.source_metadata)
            assert "completion_handler" in source_metadata
            assert source_metadata["completion_handler"] == "api.webhooks.slack.routes.handle_slack_task_completion"
    
    async def test_task_worker_calls_registered_completion_handler(self):
        """
        Business Rule: Task worker must call registered completion handler.
        Behavior: Handler is dynamically imported and called with correct parameters.
        """
        from workers.task_worker import TaskWorker
        from core.websocket_hub import WebSocketHub
        
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
                "payload": {
                    "repository": {"owner": {"login": "test"}, "name": "repo"},
                    "issue": {"number": 123}
                },
                "completion_handler": "api.webhooks.github.routes.handle_github_task_completion"
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
                payload={
                    "repository": {"owner": {"login": "test"}, "name": "repo"},
                    "issue": {"number": 123}
                },
                message="Task completed successfully",
                success=True,
                cost_usd=0.05,
                task_id="task-123",
                command=None,
                result="Clean output",
                error=None
            )
    
    async def test_task_worker_handles_missing_completion_handler(self):
        """
        Business Rule: Task worker must handle missing completion handler gracefully.
        Behavior: Returns False and logs warning if handler not found.
        """
        from workers.task_worker import TaskWorker
        from core.websocket_hub import WebSocketHub
        
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
                "payload": {"issue": {"number": 123}}
            }),
            cost_usd=0.0
        )
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        result = await worker._invoke_completion_handler(
            task_db=task_db,
            message="Test",
            success=True,
            result=None,
            error=None
        )
        
        assert result is False
