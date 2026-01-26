"""TDD Integration tests for Jira comment functionality.

Tests that Jira webhook works with comments containing @agent prefix.
"""

import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from unittest.mock import MagicMock

from workers.task_worker import TaskWorker
from core.websocket_hub import WebSocketHub
from core.database.models import TaskDB
from shared import TaskStatus


@pytest.mark.integration
class TestJiraCommentFunctionality:
    """Test Jira webhook works with comments."""
    
    @pytest.mark.asyncio
    async def test_jira_webhook_works_with_comment_containing_agent(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ):
        """
        Business Rule: Jira webhook must work with comments containing @agent prefix.
        Behavior: Comment with @agent → Task created → Completion handler registered.
        """
        monkeypatch.setenv("JIRA_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "webhookEvent": "jira:issue_comment_created",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test Issue",
                    "description": "Test"
                }
            },
            "comment": {
                "body": "@agent analyze this ticket",
                "author": {
                    "displayName": "Test User",
                    "accountType": "atlassian"
                }
            }
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {"X-Jira-Signature": signature}
        
        with patch('api.webhooks.jira.utils.redis_client.push_task', new_callable=AsyncMock) as mock_queue, \
             patch('api.webhooks.jira.utils.post_jira_comment', new_callable=AsyncMock) as mock_comment:
            mock_queue.return_value = None
            mock_comment.return_value = True
            
            response = await client.post(
                "/webhooks/jira",
                content=body,
                headers=headers
            )
            
            assert response.status_code in [200, 201], "Route should accept comment with @agent"
            data = response.json()
            
            if "task_id" in data:
                task_id = data["task_id"]
                
                result = await db.execute(
                    select(TaskDB).where(TaskDB.task_id == task_id)
                )
                task_db = result.scalar_one_or_none()
                
                assert task_db is not None, "Task should be created"
                source_metadata = json.loads(task_db.source_metadata)
                assert "completion_handler" in source_metadata, "Completion handler should be registered"
                assert source_metadata["completion_handler"] == "api.webhooks.jira.routes.handle_jira_task_completion"
                
                assert mock_queue.called, "Task should be queued"
    
    @pytest.mark.asyncio
    async def test_jira_completion_handler_posts_comment_back(
        self, db: AsyncSession
    ):
        """
        Business Rule: Jira completion handler must post comment back to ticket.
        Behavior: Handler posts formatted comment to Jira ticket.
        """
        task_db = TaskDB(
            task_id="task-jira-comment",
            session_id="session-jira-comment",
            user_id="user-jira-comment",
            assigned_agent="brain",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="analyze ticket",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "jira",
                "payload": {
                    "issue": {"key": "TEST-456", "fields": {"summary": "Test"}},
                    "comment": {"body": "@agent analyze"}
                },
                "completion_handler": "api.webhooks.jira.routes.handle_jira_task_completion",
                "command": "analyze"
            }),
            cost_usd=0.05,
            result="Analysis complete"
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
                message="Analysis complete",
                success=True,
                result="Analysis complete",
                error=None
            )
            
            assert result is True, "Completion handler should succeed"
            assert mock_post.called, "Comment should be posted to Jira"
            
            call_args = mock_post.call_args
            assert call_args[1]["message"] == "Analysis complete", "Message should be posted"
            assert call_args[1]["success"] is True, "Success flag should be True"
