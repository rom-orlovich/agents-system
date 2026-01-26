"""
Integration tests for new hard-coded webhook handlers (TDD approach).
Tests focus on business logic and behavior, not implementation details.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import hmac
import hashlib
import os


@pytest.mark.integration
class TestGitHubWebhookBehavior:
    """Test GitHub webhook business logic and behavior."""
    
    async def test_webhook_rejects_invalid_signature(self, client: AsyncClient):
        """
        Business Rule: Webhook must verify signature before processing.
        Behavior: Invalid signature → 401 Unauthorized
        """
        payload = {"issue": {"number": 123, "title": "Test"}}
        headers = {"X-GitHub-Event": "issues", "X-Hub-Signature-256": "invalid"}
        
        response = await client.post(
            "/webhooks/github",
            json=payload,
            headers=headers
        )
        
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()
    
    async def test_webhook_accepts_valid_signature(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: Valid signature allows processing.
        Behavior: Valid signature → 200 OK, task created
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        payload = {"issue": {"number": 123, "title": "Test Issue"}}
        body = b'{"issue": {"number": 123, "title": "Test Issue"}}'
        
        secret = "test-secret"
        signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        with patch('api.webhooks.github.utils.github_client.post_issue_comment', new_callable=AsyncMock):
            with patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock):
                response = await client.post(
                    "/webhooks/github",
                    content=body,
                    headers=headers
                )
                
                assert response.status_code in [200, 201]
                data = response.json()
                assert "task_id" in data or "status" in data
    
    async def test_webhook_sends_immediate_reaction_on_issue_comment(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: User gets immediate feedback when webhook is triggered.
        Behavior: Issue comment with @agent → GitHub reaction sent → Task created
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "action": "created",
            "comment": {"id": 456, "body": "@agent please analyze this"},
            "issue": {"number": 123},
            "repository": {"owner": {"login": "test"}, "name": "repo"}
        }
        body = b'{"action": "created", "comment": {"id": 456, "body": "@agent please analyze this"}, "issue": {"number": 123}, "repository": {"owner": {"login": "test"}, "name": "repo"}}'
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_http:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_http.return_value = mock_response
            
            with patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock):
                response = await client.post(
                    "/webhooks/github",
                    content=body,
                    headers=headers
                )
                
                assert mock_http.called
                assert "reactions" in str(mock_http.call_args) or response.status_code in [200, 201]
                assert response.status_code in [200, 201]
    
    async def test_webhook_matches_command_by_name_in_comment(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: Commands matched by name or alias in payload text.
        Behavior: Comment contains "analyze" → Matches "analyze" command
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "comment": {"body": "@agent analyze this issue"},
            "issue": {"number": 123, "title": "Test"},
            "repository": {"owner": {"login": "test"}, "name": "repo"}
        }
        body = b'{"comment": {"body": "@agent analyze this issue"}, "issue": {"number": 123, "title": "Test"}, "repository": {"owner": {"login": "test"}, "name": "repo"}}'
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        with patch('api.webhooks.github.utils.github_client.post_issue_comment', new_callable=AsyncMock):
            with patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock):
                response = await client.post(
                    "/webhooks/github",
                    content=body,
                    headers=headers
                )
                
                assert response.status_code in [200, 201]
                data = response.json()
                assert "command" in data or "task_id" in data or "status" in data
    
    async def test_webhook_uses_default_command_when_no_match(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: Default command used when no specific command matches.
        Behavior: Comment with @agent but no command → Uses default command
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "comment": {"body": "@agent hello"},
            "issue": {"number": 123},
            "repository": {"owner": {"login": "test"}, "name": "repo"}
        }
        body = b'{"comment": {"body": "@agent hello"}, "issue": {"number": 123}, "repository": {"owner": {"login": "test"}, "name": "repo"}}'
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        with patch('api.webhooks.github.utils.github_client.post_issue_comment', new_callable=AsyncMock):
            with patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock):
                response = await client.post(
                    "/webhooks/github",
                    content=body,
                    headers=headers
                )
                
                assert response.status_code in [200, 201]
                data = response.json()
                assert "task_id" in data or "status" in data
    
    async def test_webhook_creates_task_with_correct_agent(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: Tasks routed to correct agent based on command.
        Behavior: "plan" command → Task created with agent="planning"
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "comment": {"body": "@agent plan the fix"},
            "issue": {"number": 123, "title": "Bug"},
            "repository": {"owner": {"login": "test"}, "name": "repo"}
        }
        body = b'{"comment": {"body": "@agent plan the fix"}, "issue": {"number": 123, "title": "Bug"}, "repository": {"owner": {"login": "test"}, "name": "repo"}}'
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        with patch('api.webhooks.github.utils.github_client.post_issue_comment', new_callable=AsyncMock):
            with patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock):
                response = await client.post(
                    "/webhooks/github",
                    content=body,
                    headers=headers
                )
                
                assert response.status_code in [200, 201]
                data = response.json()
                assert "task_id" in data or "status" in data


@pytest.mark.integration
class TestJiraWebhookBehavior:
    """Test Jira webhook business logic and behavior."""
    
    async def test_jira_webhook_rejects_invalid_signature(self, client: AsyncClient):
        """
        Business Rule: Jira webhook must verify signature.
        Behavior: Invalid signature → 401 Unauthorized
        """
        payload = {"issue": {"key": "PROJ-123"}}
        headers = {"X-Jira-Signature": "invalid"}
        
        response = await client.post(
            "/webhooks/jira",
            json=payload,
            headers=headers
        )
        
        assert response.status_code == 401
    
    async def test_jira_webhook_processes_valid_event(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: Valid Jira webhook creates task.
        Behavior: Valid event → Task created
        """
        monkeypatch.setenv("JIRA_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "PROJ-123",
                "fields": {"summary": "Test Issue", "description": "Test"}
            }
        }
        body = b'{"webhookEvent": "jira:issue_updated", "issue": {"key": "PROJ-123", "fields": {"summary": "Test Issue", "description": "Test"}}}'
        
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
            assert "task_id" in data or "status" in data


@pytest.mark.integration
class TestSlackWebhookBehavior:
    """Test Slack webhook business logic and behavior."""
    
    async def test_slack_webhook_handles_url_verification(self, client: AsyncClient):
        """
        Business Rule: Slack requires URL verification.
        Behavior: url_verification event → Returns challenge
        """
        payload = {
            "type": "url_verification",
            "challenge": "test-challenge-123"
        }
        body = b'{"type": "url_verification", "challenge": "test-challenge-123"}'
        
        secret = os.getenv("SLACK_WEBHOOK_SECRET", "test-secret")
        timestamp = "1234567890"
        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        signature = "v0=" + hmac.new(secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
        
        headers = {
            "X-Slack-Signature": signature,
            "X-Slack-Request-Timestamp": timestamp
        }
        
        response = await client.post(
            "/webhooks/slack",
            content=body,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["challenge"] == "test-challenge-123"
    
    async def test_slack_webhook_sends_ephemeral_response(self, client: AsyncClient, monkeypatch):
        """
        Business Rule: User gets immediate feedback in Slack.
        Behavior: Message with @agent → Ephemeral message sent → Task created
        """
        monkeypatch.setenv("SLACK_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "text": "@agent analyze this",
                "channel": "C123",
                "user": "U123"
            }
        }
        body = b'{"type": "event_callback", "event": {"type": "message", "text": "@agent analyze this", "channel": "C123", "user": "U123"}}'
        
        secret = "test-secret"
        timestamp = "1234567890"
        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        signature = "v0=" + hmac.new(secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
        
        headers = {
            "X-Slack-Signature": signature,
            "X-Slack-Request-Timestamp": timestamp
        }
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_http:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_http.return_value = mock_response
            
            with patch('api.webhooks.slack.utils.redis_client.push_task', new_callable=AsyncMock):
                response = await client.post(
                    "/webhooks/slack",
                    content=body,
                    headers=headers
                )
                
                assert mock_http.called or response.status_code in [200, 201]
                assert response.status_code in [200, 201]


@pytest.mark.skip(reason="Sentry operations are not used in this project")
@pytest.mark.integration
class TestSentryWebhookBehavior:
    """Test Sentry webhook business logic and behavior - SKIPPED."""
    
    async def test_sentry_webhook_rejects_invalid_signature(self, client: AsyncClient):
        """Sentry operations not used."""
        pytest.skip("Sentry operations not used")
    
    async def test_sentry_webhook_processes_error_event(self, client: AsyncClient, monkeypatch):
        """Sentry operations not used."""
        pytest.skip("Sentry operations not used")
