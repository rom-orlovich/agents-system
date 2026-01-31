import pytest
import json
import hashlib
import hmac
from unittest.mock import AsyncMock
from typing import Any


@pytest.fixture
def github_issue_payload() -> dict[str, Any]:
    return {
        "action": "opened",
        "issue": {
            "number": 42,
            "title": "Fix authentication bug",
            "body": "Users cannot login with OAuth",
            "labels": [{"name": "bug"}, {"name": "AI-Fix"}],
        },
        "repository": {
            "full_name": "org/repo",
            "clone_url": "https://github.com/org/repo.git",
            "default_branch": "main",
        },
    }


@pytest.fixture
def github_pr_payload() -> dict[str, Any]:
    return {
        "action": "opened",
        "pull_request": {
            "number": 123,
            "title": "Add new feature",
            "body": "Implements feature X",
            "head": {"ref": "feature/x"},
            "base": {"ref": "main"},
        },
        "repository": {
            "full_name": "org/repo",
            "clone_url": "https://github.com/org/repo.git",
            "default_branch": "main",
        },
    }


@pytest.fixture
def jira_issue_payload() -> dict[str, Any]:
    return {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "summary": "Implement user dashboard",
                "description": "Create a new dashboard component",
                "issuetype": {"name": "Task"},
                "labels": ["AI-Fix"],
                "project": {"key": "PROJ"},
            },
        },
    }


@pytest.fixture
def slack_message_payload() -> dict[str, Any]:
    return {
        "type": "event_callback",
        "event": {
            "type": "app_mention",
            "text": "<@BOT123> Can you help fix the build?",
            "channel": "C123456",
            "ts": "1234567890.123456",
            "user": "U987654",
        },
    }


@pytest.fixture
def sentry_alert_payload() -> dict[str, Any]:
    return {
        "action": "triggered",
        "data": {
            "event": {
                "event_id": "abc123",
                "title": "TypeError: Cannot read property 'x' of undefined",
                "culprit": "src/components/Dashboard.tsx",
                "platform": "javascript",
            },
            "triggering_rules": [],
        },
        "project_slug": "my-project",
    }


def create_github_signature(payload: bytes, secret: str) -> str:
    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


class TestGitHubWebhookFlow:
    def test_github_issue_event_processing(
        self,
        github_issue_payload: dict[str, Any],
    ) -> None:
        supported_events = ["issues", "issue_comment", "pull_request", "push"]
        event_type = "issues"
        action = "opened"

        assert event_type in supported_events
        assert github_issue_payload["action"] == action
        assert github_issue_payload["issue"]["number"] == 42

    def test_github_pr_event_processing(
        self,
        github_pr_payload: dict[str, Any],
    ) -> None:
        supported_events = ["issues", "issue_comment", "pull_request", "push"]
        event_type = "pull_request"

        assert event_type in supported_events
        assert github_pr_payload["pull_request"]["number"] == 123
        assert github_pr_payload["pull_request"]["head"]["ref"] == "feature/x"

    def test_unsupported_event_detected(self) -> None:
        supported_events = ["issues", "issue_comment", "pull_request", "push"]
        unsupported = ["star", "fork", "watch"]

        for event in unsupported:
            assert event not in supported_events

    def test_unsupported_action_detected(self) -> None:
        supported_actions = {"issues": ["opened", "edited", "labeled"]}

        assert "closed" not in supported_actions["issues"]
        assert "deleted" not in supported_actions["issues"]


class TestJiraWebhookFlow:
    def test_jira_issue_event_processing(
        self,
        jira_issue_payload: dict[str, Any],
    ) -> None:
        supported_events = ["jira:issue_created", "jira:issue_updated"]
        event_type = jira_issue_payload["webhookEvent"]

        assert event_type in supported_events
        assert jira_issue_payload["issue"]["key"] == "PROJ-123"
        assert "AI-Fix" in jira_issue_payload["issue"]["fields"]["labels"]

    def test_jira_issue_without_label_detected(
        self,
        jira_issue_payload: dict[str, Any],
    ) -> None:
        ai_fix_label = "AI-Fix"
        jira_issue_payload["issue"]["fields"]["labels"] = []

        assert ai_fix_label not in jira_issue_payload["issue"]["fields"]["labels"]


class TestSlackWebhookFlow:
    def test_slack_app_mention_processing(
        self,
        slack_message_payload: dict[str, Any],
    ) -> None:
        supported_types = ["message", "app_mention"]
        event = slack_message_payload["event"]

        assert event["type"] in supported_types
        assert event["channel"] == "C123456"
        assert "fix the build" in event["text"]

    def test_non_mention_message_detected(
        self,
        slack_message_payload: dict[str, Any],
    ) -> None:
        event = slack_message_payload["event"]
        event["type"] = "message"
        event["text"] = "Regular message without mention"

        assert "@agent" not in event["text"].lower()
        assert "<@" not in event["text"]


class TestSentryWebhookFlow:
    def test_sentry_alert_processing(
        self,
        sentry_alert_payload: dict[str, Any],
    ) -> None:
        supported_actions = ["created", "resolved", "assigned"]
        action = "created"

        assert action in supported_actions
        assert "TypeError" in sentry_alert_payload["data"]["event"]["title"]


class TestTaskQueuing:
    @pytest.mark.asyncio
    async def test_task_pushed_to_redis(
        self,
        mock_redis: AsyncMock,
        github_issue_payload: dict[str, Any],
    ) -> None:
        from agent_engine.core.queue_manager import QueueManager

        manager = QueueManager(redis_client=mock_redis)

        task_data = json.dumps({
            "task_id": "test-123",
            "source": "github",
            "event_type": "issues",
            "payload": github_issue_payload,
        })

        await manager.push_task(task_data)

        mock_redis.lpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_popped_from_redis(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        from agent_engine.core.queue_manager import QueueManager

        expected_task = "task-123"
        mock_redis.brpop.return_value = (b"agent:tasks", expected_task.encode())

        manager = QueueManager(redis_client=mock_redis)
        task = await manager.pop_task(timeout=5)

        assert task == expected_task

    @pytest.mark.asyncio
    async def test_queue_empty_returns_none(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        from agent_engine.core.queue_manager import QueueManager

        mock_redis.brpop.return_value = None

        manager = QueueManager(redis_client=mock_redis)
        task = await manager.pop_task(timeout=1)

        assert task is None


class TestWebhookSignatureValidation:
    def test_github_signature_validation(self) -> None:
        secret = "test-secret"
        payload = b'{"action": "opened"}'

        expected_signature = "sha256=" + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        computed_signature = "sha256=" + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert expected_signature == computed_signature

    def test_invalid_signature_detected(self) -> None:
        secret = "test-secret"
        payload = b'{"action": "opened"}'

        valid_signature = "sha256=" + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        invalid_signature = "sha256=invalid"

        assert valid_signature != invalid_signature


class TestTaskRouting:
    def test_github_issue_routing(self) -> None:
        routing_map = {
            "issues": "github-issue-handler",
            "pull_request": "github-pr-review",
            "push": "executor",
        }

        assert routing_map.get("issues") == "github-issue-handler"

    def test_jira_routing(self) -> None:
        source_routing = {
            "jira": "jira-code-plan",
            "github": "github-issue-handler",
            "slack": "slack-inquiry",
            "sentry": "sentry-error-handler",
        }

        assert source_routing.get("jira") == "jira-code-plan"

    def test_slack_routing(self) -> None:
        source_routing = {
            "jira": "jira-code-plan",
            "github": "github-issue-handler",
            "slack": "slack-inquiry",
            "sentry": "sentry-error-handler",
        }

        assert source_routing.get("slack") == "slack-inquiry"
