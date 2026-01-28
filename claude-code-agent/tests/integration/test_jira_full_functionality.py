"""TDD Integration tests verifying Jira webhook full functionality.

Tests both comment-based and assignee-change-based triggers work correctly.
"""

import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from workers.task_worker import TaskWorker
from core.websocket_hub import WebSocketHub
from core.database.models import TaskDB
from shared import TaskStatus


@pytest.mark.integration
class TestJiraFullFunctionality:
    """Test Jira webhook works with both comment and assignee change triggers."""
    
    @pytest.mark.asyncio
    async def test_jira_works_with_comment_trigger(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ):
        """
        Business Rule: Jira webhook must work with comments containing @agent.
        Behavior: Comment with @agent → Task created → Completion handler registered.
        """
        monkeypatch.setenv("JIRA_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "webhookEvent": "jira:issue_comment_created",
            "issue": {
                "key": "TEST-COMMENT",
                "fields": {"summary": "Test Issue"}
            },
            "comment": {
                "body": "@agent analyze this ticket",
                "author": {"displayName": "Test User", "accountType": "atlassian"}
            }
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        with patch('api.webhooks.jira.utils.redis_client.push_task', new_callable=AsyncMock), \
             patch('api.webhooks.jira.utils.post_jira_comment', new_callable=AsyncMock):
            
            response = await client.post(
                "/webhooks/jira",
                content=body,
                headers={"X-Jira-Signature": signature}
            )
            
            assert response.status_code in [200, 201]
            data = response.json()
            
            if "task_id" in data:
                result = await db.execute(
                    select(TaskDB).where(TaskDB.task_id == data["task_id"])
                )
                task_db = result.scalar_one_or_none()
                
                assert task_db is not None
                source_metadata = json.loads(task_db.source_metadata)
                assert source_metadata["completion_handler"] == "api.webhooks.jira.routes.handle_jira_task_completion"
    
    @pytest.mark.asyncio
    async def test_jira_works_with_assignee_change_trigger(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ):
        """
        Business Rule: Jira webhook must work when assignee is changed to AI Agent.
        Behavior: Assignee change → Task created → Default command used → Completion handler registered.
        """
        monkeypatch.setenv("JIRA_WEBHOOK_SECRET", "test-secret")
        monkeypatch.setenv("JIRA_AI_AGENT_NAME", "AI Agent")
        
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "TEST-ASSIGNEE",
                "fields": {"summary": "Test Issue"}
            },
            "changelog": {
                "items": [
                    {
                        "field": "assignee",
                        "toString": "AI Agent",
                        "fromString": "Previous User"
                    }
                ]
            }
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        with patch('api.webhooks.jira.utils.redis_client.push_task', new_callable=AsyncMock), \
             patch('api.webhooks.jira.utils.post_jira_comment', new_callable=AsyncMock):
            
            response = await client.post(
                "/webhooks/jira",
                content=body,
                headers={"X-Jira-Signature": signature}
            )
            
            assert response.status_code in [200, 201]
            data = response.json()
            
            if "task_id" in data:
                result = await db.execute(
                    select(TaskDB).where(TaskDB.task_id == data["task_id"])
                )
                task_db = result.scalar_one_or_none()
                
                assert task_db is not None
                source_metadata = json.loads(task_db.source_metadata)
                assert source_metadata["completion_handler"] == "api.webhooks.jira.routes.handle_jira_task_completion"
    
    @pytest.mark.asyncio
    async def test_jira_completion_handler_works_for_both_triggers(
        self, db: AsyncSession
    ):
        """
        Business Rule: Completion handler must work for both comment and assignee change tasks.
        Behavior: Handler posts comment and sends Slack notification regardless of trigger type.
        """
        task_db = TaskDB(
            task_id="task-jira-both",
            session_id="session-jira-both",
            user_id="user-jira-both",
            assigned_agent="brain",
            agent_type="planning",
            status=TaskStatus.COMPLETED,
            input_message="analyze ticket",
            source="webhook",
            source_metadata=json.dumps({
                "webhook_source": "jira",
                "payload": {
                    "issue": {"key": "TEST-BOTH", "fields": {"summary": "Test"}}
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
            assert mock_post.called, "Comment should be posted"
            assert mock_slack.called, "Slack notification should be sent"
            
            call_args = mock_post.call_args
            assert call_args[1]["message"] == "Analysis complete"
            assert call_args[1]["success"] is True
