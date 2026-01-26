"""TDD Integration tests for complete webhook completion flow.

Tests the end-to-end business logic:
1. Webhook receives request → creates task with completion handler
2. Task worker processes task → calls completion handler
3. Completion handler posts comment → sends Slack notification
"""

import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy import select

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from workers.task_worker import TaskWorker
from core.websocket_hub import WebSocketHub
from core.database.models import TaskDB
from shared import TaskStatus


@pytest.mark.integration
class TestGitHubWebhookCompletionFlow:
    """Test complete GitHub webhook → task worker → completion handler flow."""
    
    @pytest.mark.asyncio
    async def test_github_webhook_creates_task_with_completion_handler(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ):
        """
        Business Rule: GitHub webhook must register completion handler in task metadata.
        Behavior: Task created with completion_handler path in source_metadata.
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "action": "created",
            "comment": {"id": 456, "body": "@agent review the pr"},
            "issue": {"number": 123, "pull_request": {}},
            "repository": {"owner": {"login": "test"}, "name": "repo"}
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        with patch('api.webhooks.github.utils.github_client.add_reaction', new_callable=AsyncMock), \
             patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock):
            
            response = await client.post(
                "/webhooks/github",
                content=body,
                headers=headers
            )
            
            assert response.status_code in [200, 201]
            
            task_id = response.json().get("task_id")
            assert task_id is not None
            
            result = await db.execute(
                select(TaskDB).where(TaskDB.task_id == task_id)
            )
            task_db = result.scalar_one_or_none()
            assert task_db is not None
            
            source_metadata = json.loads(task_db.source_metadata)
            assert "completion_handler" in source_metadata
            assert source_metadata["completion_handler"] == "api.webhooks.github.routes.handle_github_task_completion"
            assert "payload" in source_metadata
    
    @pytest.mark.asyncio
    async def test_task_worker_calls_github_completion_handler_on_success(
        self, db: AsyncSession
    ):
        """
        Business Rule: Task worker must call GitHub completion handler when task succeeds.
        Behavior: Handler receives correct parameters and posts comment + sends notification.
        """
        task_db = TaskDB(
            task_id="task-github-123",
            session_id="session-123",
            user_id="user-123",
            assigned_agent="brain",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="review pr",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "github",
                "payload": {
                    "repository": {"owner": {"login": "test"}, "name": "repo"},
                    "issue": {"number": 123, "pull_request": {}}
                },
                "completion_handler": "api.webhooks.github.routes.handle_github_task_completion",
                "command": "review pr"
            }),
            cost_usd=0.05,
            result="Review complete"
        )
        
        db.add(task_db)
        await db.commit()
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            mock_post.return_value = True
            
            result = await worker._invoke_completion_handler(
                task_db=task_db,
                message="Review complete",
                success=True,
                result="Review complete",
                error=None
            )
            
            assert result is True
            mock_post.assert_called_once()
            mock_slack.assert_called_once_with(
                task_id="task-github-123",
                webhook_source="github",
                command="review pr",
                success=True,
                result="Review complete",
                error=None
            )
    
    @pytest.mark.asyncio
    async def test_task_worker_calls_github_completion_handler_on_failure(
        self, db: AsyncSession
    ):
        """
        Business Rule: Task worker must call GitHub completion handler when task fails.
        Behavior: Handler formats error with ❌ emoji and posts comment.
        """
        task_db = TaskDB(
            task_id="task-github-fail",
            session_id="session-fail",
            user_id="user-fail",
            assigned_agent="brain",
            agent_type="planning",
            status=TaskStatus.FAILED,
            input_message="review pr",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "github",
                "payload": {
                    "repository": {"owner": {"login": "test"}, "name": "repo"},
                    "issue": {"number": 456}
                },
                "completion_handler": "api.webhooks.github.routes.handle_github_task_completion",
                "command": "review pr"
            }),
            cost_usd=0.0
        )
        
        db.add(task_db)
        await db.commit()
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            result = await worker._invoke_completion_handler(
                task_db=task_db,
                message="Task failed",
                success=False,
                result=None,
                error="Something went wrong"
            )
            
            assert result is True
            call_args = mock_post.call_args
            assert call_args[1]["message"] == "❌ Something went wrong"
            assert call_args[1]["success"] is False


@pytest.mark.integration
class TestJiraWebhookCompletionFlow:
    """Test complete Jira webhook → task worker → completion handler flow."""
    
    @pytest.mark.asyncio
    async def test_jira_webhook_creates_task_with_completion_handler(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ):
        """
        Business Rule: Jira webhook must register completion handler in task metadata.
        Behavior: Task created with completion_handler path in source_metadata.
        """
        monkeypatch.setenv("JIRA_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "TEST-123",
                "fields": {"summary": "Test Issue", "description": "Test"}
            },
            "comment": {"body": "@agent analyze this ticket"}
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {"X-Jira-Signature": signature}
        
        with patch('api.webhooks.jira.utils.redis_client.push_task', new_callable=AsyncMock):
            response = await client.post(
                "/webhooks/jira",
                content=body,
                headers=headers
            )
            
            assert response.status_code in [200, 201]
            
            task_id = response.json().get("task_id")
            if task_id:
                result = await db.execute(
                    select(TaskDB).where(TaskDB.task_id == task_id)
                )
                task_db = result.scalar_one_or_none()
                if task_db:
                    source_metadata = json.loads(task_db.source_metadata)
                    assert "completion_handler" in source_metadata
                    assert source_metadata["completion_handler"] == "api.webhooks.jira.routes.handle_jira_task_completion"
    
    @pytest.mark.asyncio
    async def test_task_worker_calls_jira_completion_handler_on_success(
        self, db: AsyncSession
    ):
        """
        Business Rule: Task worker must call Jira completion handler when task succeeds.
        Behavior: Handler posts comment and sends notification.
        """
        task_db = TaskDB(
            task_id="task-jira-123",
            session_id="session-jira",
            user_id="user-jira",
            assigned_agent="brain",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="analyze ticket",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "jira",
                "payload": {
                    "issue": {"key": "TEST-123", "fields": {"summary": "Test"}}
                },
                "completion_handler": "api.webhooks.jira.routes.handle_jira_task_completion",
                "command": "analyze ticket"
            }),
            cost_usd=0.05,
            result="Analysis complete"
        )
        
        db.add(task_db)
        await db.commit()
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        with patch('api.webhooks.jira.routes.post_jira_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            mock_post.return_value = True
            
            result = await worker._invoke_completion_handler(
                task_db=task_db,
                message="Analysis complete",
                success=True,
                result="Analysis complete",
                error=None
            )
            
            assert result is True
            mock_post.assert_called_once()
            mock_slack.assert_called_once_with(
                task_id="task-jira-123",
                webhook_source="jira",
                command="analyze ticket",
                success=True,
                result="Analysis complete",
                error=None
            )
    
    @pytest.mark.asyncio
    async def test_jira_completion_handler_formats_error_cleanly(
        self, db: AsyncSession
    ):
        """
        Business Rule: Jira errors must be formatted cleanly without emoji.
        Behavior: Error message uses error text directly.
        """
        task_db = TaskDB(
            task_id="task-jira-fail",
            session_id="session-jira-fail",
            user_id="user-jira-fail",
            assigned_agent="brain",
            agent_type="planning",
            status=TaskStatus.FAILED,
            input_message="analyze ticket",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "jira",
                "payload": {
                    "issue": {"key": "TEST-456", "fields": {"summary": "Test"}}
                },
                "completion_handler": "api.webhooks.jira.routes.handle_jira_task_completion",
                "command": "analyze ticket"
            }),
            cost_usd=0.0
        )
        
        db.add(task_db)
        await db.commit()
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        with patch('api.webhooks.jira.routes.post_jira_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            result = await worker._invoke_completion_handler(
                task_db=task_db,
                message="Task failed",
                success=False,
                result=None,
                error="Something went wrong"
            )
            
            assert result is True
            call_args = mock_post.call_args
            assert call_args[1]["message"] == "Something went wrong"
            assert "❌" not in call_args[1]["message"]


@pytest.mark.integration
class TestSlackWebhookCompletionFlow:
    """Test complete Slack webhook → task worker → completion handler flow."""
    
    @pytest.mark.asyncio
    async def test_slack_webhook_creates_task_with_completion_handler(
        self, client: AsyncClient, db: AsyncSession
    ):
        """
        Business Rule: Slack webhook must register completion handler in task metadata.
        Behavior: Task created with completion_handler path in source_metadata.
        """
        payload = {
            "event": {
                "type": "app_mention",
                "text": "<@U123456> @agent help me",
                "user": "U123456",
                "channel": "C123456",
                "ts": "1234567890.123456"
            }
        }
        
        with patch('api.webhooks.slack.utils.redis_client.push_task', new_callable=AsyncMock):
            response = await client.post(
                "/webhooks/slack",
                json=payload
            )
            
            assert response.status_code in [200, 201]
            
            task_id = response.json().get("task_id")
            if task_id:
                result = await db.execute(
                    select(TaskDB).where(TaskDB.task_id == task_id)
                )
                task_db = result.scalar_one_or_none()
                if task_db:
                    source_metadata = json.loads(task_db.source_metadata)
                    assert "completion_handler" in source_metadata
                    assert source_metadata["completion_handler"] == "api.webhooks.slack.routes.handle_slack_task_completion"
    
    @pytest.mark.asyncio
    async def test_task_worker_calls_slack_completion_handler_on_success(
        self, db: AsyncSession
    ):
        """
        Business Rule: Task worker must call Slack completion handler when task succeeds.
        Behavior: Handler posts message and sends notification.
        """
        task_db = TaskDB(
            task_id="task-slack-123",
            session_id="session-slack",
            user_id="user-slack",
            assigned_agent="brain",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="help me",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "slack",
                "payload": {
                    "event": {
                        "channel": "C123456",
                        "text": "@agent help",
                        "user": "U123456",
                        "ts": "1234567890.123456"
                    }
                },
                "completion_handler": "api.webhooks.slack.routes.handle_slack_task_completion",
                "command": "help"
            }),
            cost_usd=0.05,
            result="Help response"
        )
        
        db.add(task_db)
        await db.commit()
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        with patch('api.webhooks.slack.routes.post_slack_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.slack.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            mock_post.return_value = True
            
            result = await worker._invoke_completion_handler(
                task_db=task_db,
                message="Help response",
                success=True,
                result="Help response",
                error=None
            )
            
            assert result is True
            mock_post.assert_called_once()
            mock_slack.assert_called_once_with(
                task_id="task-slack-123",
                webhook_source="slack",
                command="help",
                success=True,
                result="Help response",
                error=None
            )
    
    @pytest.mark.asyncio
    async def test_slack_completion_handler_formats_error_cleanly(
        self, db: AsyncSession
    ):
        """
        Business Rule: Slack errors must be formatted cleanly without emoji.
        Behavior: Error message uses error text directly.
        """
        task_db = TaskDB(
            task_id="task-slack-fail",
            session_id="session-slack-fail",
            user_id="user-slack-fail",
            assigned_agent="brain",
            agent_type="planning",
            status=TaskStatus.FAILED,
            input_message="help me",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "slack",
                "payload": {
                    "event": {
                        "channel": "C123456",
                        "text": "@agent help",
                        "user": "U123456",
                        "ts": "1234567890.123456"
                    }
                },
                "completion_handler": "api.webhooks.slack.routes.handle_slack_task_completion",
                "command": "help"
            }),
            cost_usd=0.0
        )
        
        db.add(task_db)
        await db.commit()
        
        ws_hub = MagicMock(spec=WebSocketHub)
        worker = TaskWorker(ws_hub)
        
        with patch('api.webhooks.slack.routes.post_slack_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.slack.routes.send_slack_notification', new_callable=AsyncMock):
            mock_post.return_value = True
            
            result = await worker._invoke_completion_handler(
                task_db=task_db,
                message="Task failed",
                success=False,
                result=None,
                error="Something went wrong"
            )
            
            assert result is True
            call_args = mock_post.call_args
            assert call_args[1]["message"] == "Something went wrong"
            assert "❌" not in call_args[1]["message"]


@pytest.mark.integration
class TestEndToEndWebhookCompletionFlow:
    """Test complete end-to-end flow: webhook → task creation → worker → completion."""
    
    @pytest.mark.asyncio
    async def test_complete_github_flow_from_webhook_to_completion(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ):
        """
        Business Rule: Complete flow must work end-to-end.
        Behavior: Webhook → Task created → Worker processes → Handler posts comment.
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "action": "created",
            "comment": {"id": 789, "body": "@agent review"},
            "issue": {"number": 999, "pull_request": {}},
            "repository": {"owner": {"login": "test"}, "name": "repo"}
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        with patch('api.webhooks.github.utils.github_client.add_reaction', new_callable=AsyncMock), \
             patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock), \
             patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            mock_post.return_value = True
            
            response = await client.post(
                "/webhooks/github",
                content=body,
                headers=headers
            )
            
            assert response.status_code in [200, 201]
            task_id = response.json().get("task_id")
            
            if task_id:
                result = await db.execute(
                    select(TaskDB).where(TaskDB.task_id == task_id)
                )
                task_db = result.scalar_one_or_none()
                
                if task_db:
                    task_db.status = TaskStatus.COMPLETED
                    task_db.result = "Review complete"
                    task_db.cost_usd = 0.05
                    await db.commit()
                    
                    await db.refresh(task_db)
                    
                    ws_hub = MagicMock(spec=WebSocketHub)
                    worker = TaskWorker(ws_hub)
                    
                    await worker._invoke_completion_handler(
                        task_db=task_db,
                        message="Review complete",
                        success=True,
                        result="Review complete",
                        error=None
                    )
                    
                    mock_post.assert_called()
                    mock_slack.assert_called()
