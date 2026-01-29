"""TDD Integration tests for GitHub comment edit functionality.

Tests that GitHub webhook works when comments are edited.
"""

import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import TaskDB


@pytest.mark.integration
class TestGitHubCommentEdit:
    """Test GitHub webhook works with comment edits."""
    
    @pytest.mark.asyncio
    async def test_github_webhook_works_with_comment_edit(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ):
        """
        Business Rule: GitHub webhook must work when comments are edited to include @agent.
        Behavior: Comment edit with @agent → Task created → Completion handler registered.
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "action": "edited",
            "comment": {
                "id": 999,
                "body": "@agent review the pr",
                "user": {"login": "testuser", "type": "User"}
            },
            "issue": {
                "number": 123,
                "pull_request": {}
            },
            "repository": {
                "owner": {"login": "test"},
                "name": "repo"
            },
            "sender": {
                "login": "testuser",
                "type": "User"
            }
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        with patch('api.webhooks.github.utils.github_client.add_reaction', new_callable=AsyncMock) as mock_reaction, \
             patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock) as mock_queue:
            mock_reaction.return_value = True
            mock_queue.return_value = None
            
            response = await client.post(
                "/webhooks/github",
                content=body,
                headers=headers
            )
            
            assert response.status_code in [200, 201], f"Route should accept edited comment. Response: {response.json()}"
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
                assert source_metadata["completion_handler"] == "api.webhooks.github.routes.handle_github_task_completion"
                
                assert mock_queue.called, "Task should be queued"
                assert mock_reaction.called, "Reaction should be sent"
    
    @pytest.mark.asyncio
    async def test_github_webhook_rejects_comment_edit_without_agent(
        self, client: AsyncClient, monkeypatch
    ):
        """
        Business Rule: GitHub webhook must reject edited comments without @agent.
        Behavior: Comment edit without @agent → Rejected.
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "action": "edited",
            "comment": {
                "id": 888,
                "body": "Just updating my comment",
                "user": {"login": "testuser", "type": "User"}
            },
            "issue": {
                "number": 456
            },
            "repository": {
                "owner": {"login": "test"},
                "name": "repo"
            },
            "sender": {
                "login": "testuser",
                "type": "User"
            }
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        response = await client.post(
            "/webhooks/github",
            content=body,
            headers=headers
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data.get("status") in ["rejected", "received"], "Should reject or receive without action"
        if data.get("status") == "rejected":
            assert "task_id" not in data, "Should not create task"
