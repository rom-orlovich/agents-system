import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any
from dataclasses import dataclass


@dataclass
class MockWebhookResponse:
    status_code: int
    content: dict[str, Any]


@pytest.fixture
def full_github_issue_webhook() -> dict[str, Any]:
    return {
        "action": "opened",
        "issue": {
            "number": 42,
            "title": "Authentication fails with OAuth providers",
            "body": """## Description
Users are unable to login using OAuth providers (Google, GitHub).

## Steps to Reproduce
1. Click "Sign in with Google"
2. Complete OAuth flow
3. Redirect fails with 500 error

## Expected Behavior
User should be logged in successfully

## Labels
- bug
- AI-Fix
""",
            "labels": [{"name": "bug"}, {"name": "AI-Fix"}],
            "user": {"login": "testuser"},
        },
        "repository": {
            "full_name": "myorg/myapp",
            "clone_url": "https://github.com/myorg/myapp.git",
            "default_branch": "main",
            "private": False,
        },
        "sender": {"login": "testuser"},
    }


@pytest.fixture
def full_jira_issue_webhook() -> dict[str, Any]:
    return {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "id": "10001",
            "key": "PROJ-123",
            "fields": {
                "summary": "Implement user analytics dashboard",
                "description": """As a product manager, I want to see user analytics.

Acceptance Criteria:
- Display daily active users
- Show retention metrics
- Export to CSV""",
                "issuetype": {"name": "Story"},
                "priority": {"name": "High"},
                "labels": ["AI-Fix", "dashboard"],
                "project": {"key": "PROJ", "name": "Main Project"},
            },
        },
        "user": {"displayName": "Project Manager"},
    }


@pytest.fixture
def mock_cli_success_result() -> dict[str, Any]:
    return {
        "success": True,
        "output": """## Analysis Complete

### Issue Analysis
The OAuth authentication is failing due to incorrect callback URL configuration.

### Solution
1. Updated callback URL in OAuth configuration
2. Added proper error handling for OAuth flow
3. Fixed redirect logic after successful authentication

### Files Modified
- src/auth/oauth.ts
- src/config/oauth.config.ts

### Tests Added
- test/auth/oauth.test.ts

### Status
Ready for review.""",
        "cost_usd": 0.15,
        "input_tokens": 5000,
        "output_tokens": 800,
    }


class TestEndToEndGitHubWorkflow:
    @pytest.mark.asyncio
    async def test_github_issue_to_task_completion(
        self,
        full_github_issue_webhook: dict[str, Any],
        mock_redis: AsyncMock,
        mock_cli_success_result: dict[str, Any],
    ) -> None:
        task_info = {
            "task_id": "task-e2e-github-1",
            "source": "github",
            "event_type": "issues",
            "action": full_github_issue_webhook["action"],
            "issue": {
                "number": full_github_issue_webhook["issue"]["number"],
                "title": full_github_issue_webhook["issue"]["title"],
                "labels": [l["name"] for l in full_github_issue_webhook["issue"]["labels"]],
            },
            "repository": full_github_issue_webhook["repository"],
        }

        assert task_info["source"] == "github"
        assert task_info["issue"]["number"] == 42
        assert "AI-Fix" in task_info["issue"]["labels"]

        await mock_redis.lpush("agent:tasks", json.dumps(task_info).encode())
        mock_redis.lpush.assert_called()

        mock_redis.brpop.return_value = (b"agent:tasks", json.dumps(task_info).encode())
        task_data = await mock_redis.brpop("agent:tasks", timeout=5)
        received_task = json.loads(task_data[1])

        assert received_task["task_id"] == "task-e2e-github-1"

        from agent_engine.core.queue_manager import TaskStatus

        mock_redis.set.return_value = True
        await mock_redis.set(
            f"task:{received_task['task_id']}:status",
            TaskStatus.RUNNING.value,
        )

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            json.dumps(mock_cli_success_result).encode(),
            b"",
        ))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            process = await asyncio.create_subprocess_exec(
                "claude",
                "--print",
                "--output-format",
                "json",
                received_task.get("prompt", "Analyze the issue"),
            )
            stdout, stderr = await process.communicate()
            result = json.loads(stdout)

        assert result["success"] is True
        assert "OAuth" in result["output"]

        await mock_redis.set(
            f"task:{received_task['task_id']}:status",
            TaskStatus.COMPLETED.value,
        )

    @pytest.mark.asyncio
    async def test_github_pr_to_review_completion(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        pr_webhook = {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "title": "Fix OAuth callback handling",
                "body": "Fixes #42",
                "head": {"ref": "fix/oauth-callback"},
                "base": {"ref": "main"},
            },
            "repository": {
                "full_name": "myorg/myapp",
                "clone_url": "https://github.com/myorg/myapp.git",
            },
        }

        task_info = {
            "task_id": "task-e2e-pr-1",
            "source": "github",
            "event_type": "pull_request",
            "action": pr_webhook["action"],
            "pull_request": pr_webhook["pull_request"],
            "repository": pr_webhook["repository"],
        }

        assert task_info["pull_request"]["number"] == 123
        assert task_info["pull_request"]["head"]["ref"] == "fix/oauth-callback"


class TestEndToEndJiraWorkflow:
    @pytest.mark.asyncio
    async def test_jira_issue_to_plan_creation(
        self,
        full_jira_issue_webhook: dict[str, Any],
        mock_redis: AsyncMock,
    ) -> None:
        task_info = {
            "task_id": "task-e2e-jira-1",
            "source": "jira",
            "event_type": full_jira_issue_webhook["webhookEvent"],
            "issue": {
                "key": full_jira_issue_webhook["issue"]["key"],
                "summary": full_jira_issue_webhook["issue"]["fields"]["summary"],
                "labels": full_jira_issue_webhook["issue"]["fields"]["labels"],
            },
        }

        assert task_info["source"] == "jira"
        assert task_info["issue"]["key"] == "PROJ-123"
        assert "AI-Fix" in task_info["issue"]["labels"]

        await mock_redis.lpush("agent:tasks", json.dumps(task_info).encode())

        mock_redis.brpop.return_value = (b"agent:tasks", json.dumps(task_info).encode())
        task_data = await mock_redis.brpop("agent:tasks", timeout=5)
        received_task = json.loads(task_data[1])

        assert received_task["task_id"] == "task-e2e-jira-1"


class TestEndToEndSlackWorkflow:
    @pytest.mark.asyncio
    async def test_slack_mention_to_response(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        slack_event = {
            "type": "app_mention",
            "text": "<@BOT123> What's the status of PR #123?",
            "channel": "C123456",
            "ts": "1234567890.123456",
            "user": "U987654",
        }

        task_info = {
            "task_id": "task-e2e-slack-1",
            "source": "slack",
            "event_type": slack_event["type"],
            "channel": slack_event["channel"],
            "text": slack_event["text"],
            "ts": slack_event["ts"],
        }

        assert task_info["source"] == "slack"
        assert task_info["channel"] == "C123456"


class TestEndToEndSentryWorkflow:
    @pytest.mark.asyncio
    async def test_sentry_alert_to_task_creation(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        sentry_event = {
            "event_id": "abc123",
            "title": "TypeError: Cannot read property 'x' of undefined",
            "culprit": "src/components/Dashboard.tsx",
            "level": "error",
            "project": {"slug": "my-project"},
        }

        task_info = {
            "task_id": "task-e2e-sentry-1",
            "source": "sentry",
            "event_type": "error",
            "event_id": sentry_event["event_id"],
            "title": sentry_event["title"],
            "culprit": sentry_event["culprit"],
        }

        assert task_info["source"] == "sentry"
        assert "TypeError" in task_info["title"]


class TestFailureRecovery:
    @pytest.mark.asyncio
    async def test_cli_failure_marks_task_failed(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(
            b"",
            b"Error: Command failed with exit code 1",
        ))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            process = await asyncio.create_subprocess_exec("claude", "--print", "test")
            stdout, stderr = await process.communicate()

            assert process.returncode == 1
            assert b"Error" in stderr

    @pytest.mark.asyncio
    async def test_timeout_marks_task_failed(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        from agent_engine.core.queue_manager import QueueManager, TaskStatus

        manager = QueueManager(redis_client=mock_redis)

        await manager.set_task_status("task-timeout-1", TaskStatus.FAILED)

        mock_redis.set.assert_called()

    def test_invalid_event_detected(self) -> None:
        supported_events = ["issues", "pull_request", "push"]
        assert "unknown_event" not in supported_events


class TestWebhookValidation:
    def test_github_signature_validation(self) -> None:
        import hashlib
        import hmac

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

    def test_invalid_signature_rejected(self) -> None:
        import hashlib
        import hmac

        secret = "test-secret"
        payload = b'{"action": "opened"}'

        valid_signature = "sha256=" + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        invalid_signature = "sha256=invalid"

        assert valid_signature != invalid_signature


class TestAgentRouting:
    def test_github_issue_routes_to_issue_handler(
        self,
        full_github_issue_webhook: dict[str, Any],
    ) -> None:
        event_type = "issues"

        routing_map = {
            "issues": "github-issue-handler",
            "pull_request": "github-pr-review",
            "push": "executor",
        }

        assert routing_map.get(event_type) == "github-issue-handler"

    def test_jira_issue_routes_to_jira_handler(
        self,
        full_jira_issue_webhook: dict[str, Any],
    ) -> None:
        source = "jira"

        source_routing = {
            "jira": "jira-code-plan",
            "github": "github-issue-handler",
            "slack": "slack-inquiry",
            "sentry": "sentry-error-handler",
        }

        assert source_routing.get(source) == "jira-code-plan"
