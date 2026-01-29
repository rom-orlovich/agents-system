"""
Integration tests for webhook validation within webhook handlers.
Tests that validation is properly integrated with business logic.
"""

import pytest
import json
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import hmac
import hashlib


@pytest.mark.integration
class TestGitHubWebhookValidationIntegration:
    """Test GitHub webhook validation integration with handler."""
    
    async def test_webhook_rejects_payload_without_agent(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: GitHub webhook without @agent should be rejected.
        Behavior: Invalid payload → 200 OK with rejected status
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        import json
        
        payload = {
            "action": "created",
            "comment": {
                "body": "This is a regular comment without @agent",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123}
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
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert "activation rules" in data["message"].lower()
    
    async def test_webhook_accepts_payload_with_valid_agent_command(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: GitHub webhook with @agent and valid command should pass validation.
        Behavior: Valid payload → Processing continues
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        import json
        
        payload = {
            "action": "created",
            "comment": {
                "id": 456,
                "body": "@agent review this PR",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {
                "id": 111,
                "name": "repo",
                "full_name": "owner/repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False
            },
            "issue": {"number": 123, "pull_request": {}},
            "sender": {"login": "testuser", "id": 789, "type": "User"}
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        with patch('api.webhooks.github.utils.github_client.add_reaction', new_callable=AsyncMock), \
             patch('api.webhooks.github.utils.github_client.post_issue_comment', new_callable=AsyncMock), \
             patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock):
            response = await client.post(
                "/webhooks/github",
                content=body,
                headers=headers
            )

            assert response.status_code in [200, 201]
            data = response.json()
            assert data["status"] != "rejected"
    
    async def test_webhook_rejects_invalid_command(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: GitHub webhook with @agent but invalid command should be rejected.
        Behavior: Invalid command → Rejected status
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        import json
        
        payload = {
            "action": "created",
            "comment": {
                "body": "@agent invalidcommand",
                "user": {"login": "testuser", "type": "User"}
            },
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123}
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
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert "invalid command" in data.get("message", "").lower() or "activation rules" in data.get("message", "").lower()


@pytest.mark.integration
class TestJiraWebhookValidationIntegration:
    """Test Jira webhook validation integration with handler."""
    
    async def test_jira_webhook_rejects_comment_without_agent(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: Jira webhook comment without @agent should be rejected.
        Behavior: Invalid payload → Rejected status
        """
        monkeypatch.setenv("JIRA_WEBHOOK_SECRET", "test-secret")
        
        import json
        
        payload = {
            "webhookEvent": "comment_created",
            "comment": {
                "body": "This is a regular comment",
                "author": {"displayName": "testuser"}
            },
            "issue": {"key": "PROJ-123"}
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {"X-Jira-Signature": signature}
        
        response = await client.post(
            "/webhooks/jira",
            content=body,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
    
    async def test_jira_webhook_accepts_assignee_change_to_ai_agent(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: Jira webhook with assignee change to AI Agent should pass.
        Behavior: Valid assignee change → Processing continues
        """
        monkeypatch.setenv("JIRA_WEBHOOK_SECRET", "test-secret")
        
        import json
        
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "assignee": {
                        "displayName": "AI Agent",
                        "accountId": "ai-agent-id"
                    }
                }
            },
            "changelog": {
                "items": [{
                    "field": "assignee",
                    "toString": "AI Agent"
                }]
            }
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
            data = response.json()
            assert data["status"] != "rejected"


@pytest.mark.integration
class TestSlackWebhookValidationIntegration:
    """Test Slack webhook validation integration with handler."""
    
    async def test_slack_webhook_rejects_message_without_agent(self, client: AsyncClient):
        """
        Business Rule: Slack webhook without @agent should be rejected.
        Behavior: Invalid payload → Rejected status
        """
        payload = {
            "event": {
                "type": "app_mention",
                "text": "<@U123456> Hello, how are you?",
                "user": "U123456",
                "channel": "C123456"
            }
        }
        
        response = await client.post(
            "/webhooks/slack",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
    
    async def test_slack_webhook_accepts_message_with_valid_command(self, client: AsyncClient):
        """
        Business Rule: Slack webhook with @agent and valid command should pass.
        Behavior: Valid payload → Processing continues
        """
        payload = {
            "event": {
                "type": "app_mention",
                "text": "<@U123456> @agent analyze this issue",
                "user": "U123456",
                "channel": "C123456"
            }
        }
        
        with patch('api.webhooks.slack.utils.redis_client.push_task', new_callable=AsyncMock):
            response = await client.post(
                "/webhooks/slack",
                json=payload
            )
            
            assert response.status_code in [200, 201]
            data = response.json()
            assert data["status"] != "rejected"
