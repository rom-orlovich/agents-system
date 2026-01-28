"""Integration tests for webhook route full flow."""

import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from api.webhooks.github.constants import (
    PROVIDER_NAME as GITHUB_PROVIDER,
    STATUS_ACCEPTED,
    STATUS_REJECTED,
    STATUS_RECEIVED,
    MESSAGE_DOES_NOT_MEET_RULES as GITHUB_MSG_DOES_NOT_MEET_RULES,
    MESSAGE_NO_COMMAND_MATCHED as GITHUB_MSG_NO_COMMAND,
)
from api.webhooks.jira.constants import (
    PROVIDER_NAME as JIRA_PROVIDER,
    STATUS_PROCESSED as JIRA_STATUS_PROCESSED,
    STATUS_REJECTED as JIRA_STATUS_REJECTED,
    MESSAGE_DOES_NOT_MEET_RULES as JIRA_MSG_DOES_NOT_MEET_RULES,
)
from api.webhooks.slack.constants import (
    PROVIDER_NAME as SLACK_PROVIDER,
    STATUS_PROCESSED as SLACK_STATUS_PROCESSED,
    STATUS_REJECTED as SLACK_STATUS_REJECTED,
    TYPE_URL_VERIFICATION,
)


def create_github_signature(payload: dict, secret: str) -> str:
    """Create GitHub webhook signature."""
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def create_slack_signature(body: bytes, secret: str, timestamp: str) -> str:
    """Create Slack request signature."""
    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    signature = hmac.new(secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
    return f"v0={signature}"


@pytest.mark.integration
class TestGitHubWebhookRouteFlow:
    """Test GitHub webhook route full flow."""

    @pytest.fixture
    def github_issue_comment_payload(self):
        """Valid GitHub issue_comment payload with @agent command."""
        return {
            "action": "created",
            "repository": {
                "owner": {"login": "test-owner", "type": "User"},
                "name": "test-repo",
                "full_name": "test-owner/test-repo"
            },
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body"
            },
            "comment": {
                "id": 456,
                "body": "@agent analyze this issue"
            },
            "sender": {
                "login": "test-user",
                "type": "User"
            }
        }

    @pytest.fixture
    def github_headers(self):
        """Standard GitHub webhook headers."""
        return {
            "X-GitHub-Event": "issue_comment",
            "Content-Type": "application/json"
        }

    async def test_github_webhook_rejects_invalid_signature(self, client: AsyncClient, github_issue_comment_payload, github_headers):
        """GitHub webhook rejects requests with invalid signature."""
        with patch.dict('os.environ', {'GITHUB_WEBHOOK_SECRET': 'test-secret'}):
            github_headers["X-Hub-Signature-256"] = "sha256=invalid"

            response = await client.post(
                "/webhooks/github",
                json=github_issue_comment_payload,
                headers=github_headers
            )

            assert response.status_code == 401

    async def test_github_webhook_skips_bot_comments(self, client: AsyncClient, github_headers):
        """GitHub webhook skips bot-generated comments (no command matched)."""
        payload = {
            "action": "created",
            "repository": {
                "owner": {"login": "test-owner", "type": "User"},
                "name": "test-repo"
            },
            "issue": {"number": 123},
            "comment": {"id": 456, "body": "@agent test"},
            "sender": {"login": "github-actions[bot]", "type": "Bot"}
        }

        with patch('api.webhooks.github.routes.verify_github_signature', new_callable=AsyncMock):
            response = await client.post(
                "/webhooks/github",
                json=payload,
                headers=github_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == STATUS_RECEIVED
            assert data["actions"] == 0

    async def test_github_webhook_rejects_no_agent_command(self, client: AsyncClient, github_headers):
        """GitHub webhook rejects comments without @agent command."""
        payload = {
            "action": "created",
            "repository": {
                "owner": {"login": "test-owner", "type": "User"},
                "name": "test-repo"
            },
            "issue": {"number": 123},
            "comment": {"id": 456, "body": "just a regular comment"},
            "sender": {"login": "test-user", "type": "User"}
        }

        with patch('api.webhooks.github.routes.verify_github_signature', new_callable=AsyncMock):
            response = await client.post(
                "/webhooks/github",
                json=payload,
                headers=github_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in [STATUS_REJECTED, STATUS_RECEIVED]

    async def test_github_webhook_full_flow_success(self, client: AsyncClient, github_issue_comment_payload, github_headers):
        """GitHub webhook processes valid command and creates task."""
        with patch('api.webhooks.github.routes.verify_github_signature', new_callable=AsyncMock), \
             patch('api.webhooks.github.routes.send_github_immediate_response', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.github.routes.create_github_task', new_callable=AsyncMock, return_value="task-123"):

            response = await client.post(
                "/webhooks/github",
                json=github_issue_comment_payload,
                headers=github_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == STATUS_ACCEPTED
            assert "task_id" in data
            assert data["task_id"] == "task-123"
            assert "completion_handler" in data

    async def test_github_webhook_immediate_response_failure(self, client: AsyncClient, github_issue_comment_payload, github_headers):
        """GitHub webhook rejects when immediate response fails."""
        with patch('api.webhooks.github.routes.verify_github_signature', new_callable=AsyncMock), \
             patch('api.webhooks.github.routes.send_github_immediate_response', new_callable=AsyncMock, return_value=False):

            response = await client.post(
                "/webhooks/github",
                json=github_issue_comment_payload,
                headers=github_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == STATUS_REJECTED
            assert "error" in data


@pytest.mark.integration
class TestJiraWebhookRouteFlow:
    """Test Jira webhook route full flow."""

    @pytest.fixture
    def jira_comment_payload(self):
        """Valid Jira comment payload with @agent command."""
        return {
            "webhookEvent": "comment_created",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test Issue",
                    "description": "Test description",
                    "project": {"key": "TEST"}
                }
            },
            "comment": {
                "id": "10001",
                "body": "@agent analyze this ticket",
                "author": {
                    "displayName": "Test User",
                    "accountId": "123"
                }
            },
            "user": {
                "displayName": "Test User",
                "accountId": "123"
            }
        }

    async def test_jira_webhook_rejects_validation_failure(self, client: AsyncClient):
        """Jira webhook rejects payloads that don't meet validation rules."""
        payload = {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "key": "TEST-123",
                "fields": {"summary": "Test"}
            }
        }

        with patch('api.webhooks.jira.routes.verify_jira_signature', new_callable=AsyncMock):
            response = await client.post(
                "/webhooks/jira",
                json=payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == JIRA_STATUS_REJECTED

    async def test_jira_webhook_full_flow_success(self, client: AsyncClient, jira_comment_payload):
        """Jira webhook processes valid command and creates task."""
        with patch('api.webhooks.jira.routes.verify_jira_signature', new_callable=AsyncMock), \
             patch('api.webhooks.jira.routes.validate_jira_webhook') as mock_validate, \
             patch('api.webhooks.jira.routes.match_jira_command', new_callable=AsyncMock) as mock_match, \
             patch('api.webhooks.jira.routes.send_jira_immediate_response', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.jira.routes.create_jira_task', new_callable=AsyncMock, return_value="task-456"):

            mock_validate.return_value = MagicMock(is_valid=True)
            mock_match.return_value = MagicMock(name="analyze")

            response = await client.post(
                "/webhooks/jira",
                json=jira_comment_payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == JIRA_STATUS_PROCESSED
            assert "task_id" in data
            assert data["task_id"] == "task-456"


@pytest.mark.integration
class TestSlackWebhookRouteFlow:
    """Test Slack webhook route full flow."""

    @pytest.fixture
    def slack_mention_payload(self):
        """Valid Slack app_mention payload."""
        return {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "channel": "C123456",
                "user": "U123456",
                "text": "<@U_BOT_ID> analyze this",
                "ts": "1234567890.123456"
            },
            "team_id": "T123456"
        }

    async def test_slack_url_verification(self, client: AsyncClient):
        """Slack URL verification challenge is handled."""
        payload = {
            "type": TYPE_URL_VERIFICATION,
            "challenge": "test-challenge-token"
        }

        response = await client.post(
            "/webhooks/slack",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["challenge"] == "test-challenge-token"

    async def test_slack_webhook_rejects_validation_failure(self, client: AsyncClient, slack_mention_payload):
        """Slack webhook rejects payloads that don't meet validation rules."""
        with patch('api.webhooks.slack.routes.verify_slack_signature', new_callable=AsyncMock), \
             patch('api.webhooks.slack.routes.validate_slack_webhook') as mock_validate:

            mock_validate.return_value = MagicMock(is_valid=False, error_message="Test rejection")

            response = await client.post(
                "/webhooks/slack",
                json=slack_mention_payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == SLACK_STATUS_REJECTED

    async def test_slack_webhook_full_flow_success(self, client: AsyncClient, slack_mention_payload):
        """Slack webhook processes valid command and creates task."""
        with patch('api.webhooks.slack.routes.verify_slack_signature', new_callable=AsyncMock), \
             patch('api.webhooks.slack.routes.validate_slack_webhook') as mock_validate, \
             patch('api.webhooks.slack.routes.match_slack_command', new_callable=AsyncMock) as mock_match, \
             patch('api.webhooks.slack.routes.send_slack_immediate_response', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.slack.routes.create_slack_task', new_callable=AsyncMock, return_value="task-789"):

            mock_validate.return_value = MagicMock(is_valid=True)
            mock_match.return_value = MagicMock(name="analyze")

            response = await client.post(
                "/webhooks/slack",
                json=slack_mention_payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == SLACK_STATUS_PROCESSED
            assert "task_id" in data
            assert data["task_id"] == "task-789"


@pytest.mark.integration
class TestWebhookCompletionHandlers:
    """Test webhook completion handlers."""

    async def test_github_completion_handler_posts_comment(self):
        """GitHub completion handler posts comment to PR/issue."""
        from api.webhooks.github.routes import handle_github_task_completion

        payload = {
            "repository": {"owner": {"login": "test"}, "name": "repo"},
            "issue": {"number": 123}
        }

        with patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock, return_value=True) as mock_post, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock):

            result = await handle_github_task_completion(
                payload=payload,
                message="Task completed",
                success=True,
                cost_usd=0.05,
                task_id="task-123"
            )

            assert result is True
            mock_post.assert_called_once()

    async def test_jira_completion_handler_posts_comment(self):
        """Jira completion handler posts comment to ticket."""
        from api.webhooks.jira.routes import handle_jira_task_completion

        payload = {
            "issue": {
                "key": "TEST-123",
                "fields": {"summary": "Test"}
            }
        }

        with patch('api.webhooks.jira.routes.post_jira_task_comment', new_callable=AsyncMock, return_value=True) as mock_post, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock):

            result = await handle_jira_task_completion(
                payload=payload,
                message="Task completed",
                success=True,
                cost_usd=0.05,
                task_id="task-456"
            )

            assert result is True
            mock_post.assert_called_once()

    async def test_slack_completion_handler_posts_message(self):
        """Slack completion handler posts message to thread."""
        from api.webhooks.slack.routes import handle_slack_task_completion

        payload = {
            "event": {
                "channel": "C123456",
                "ts": "1234567890.123456"
            }
        }

        with patch('api.webhooks.slack.routes.post_slack_task_comment', new_callable=AsyncMock, return_value=True) as mock_post, \
             patch('api.webhooks.slack.routes.send_slack_notification', new_callable=AsyncMock):

            result = await handle_slack_task_completion(
                payload=payload,
                message="Task completed",
                success=True,
                cost_usd=0.05,
                task_id="task-789"
            )

            assert result is True
            mock_post.assert_called_once()
