"""
Tests for domain models - written first following TDD approach.

These tests define the expected behavior of our domain models:
- Webhook payload models (GitHub, Jira, Slack)
- Task completion models
- Routing models
- Notification models
- Result types
"""

import pytest
from datetime import datetime, timezone
from typing import Optional


# =============================================================================
# TEST: WebhookSource Enum
# =============================================================================

class TestWebhookSource:
    """Tests for WebhookSource enum."""

    def test_webhook_source_values(self):
        """Test that WebhookSource has expected values."""
        from domain.models import WebhookSource

        assert WebhookSource.GITHUB == "github"
        assert WebhookSource.JIRA == "jira"
        assert WebhookSource.SLACK == "slack"

    def test_webhook_source_from_string(self):
        """Test creating WebhookSource from string."""
        from domain.models import WebhookSource

        assert WebhookSource("github") == WebhookSource.GITHUB
        assert WebhookSource("jira") == WebhookSource.JIRA
        assert WebhookSource("slack") == WebhookSource.SLACK


# =============================================================================
# TEST: GitHub Webhook Payload
# =============================================================================

class TestGitHubWebhookPayload:
    """Tests for GitHubWebhookPayload model."""

    def test_minimal_payload(self):
        """Test creating payload with minimal data."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
        )

        assert payload.repository["name"] == "test-repo"
        assert payload.comment is None
        assert payload.issue is None
        assert payload.pull_request is None

    def test_payload_with_comment(self):
        """Test payload with issue comment."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
            comment={"id": 12345, "body": "@agent review this PR"},
        )

        assert payload.comment["id"] == 12345
        assert payload.comment["body"] == "@agent review this PR"

    def test_payload_with_issue(self):
        """Test payload with issue data."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
            issue={"number": 42, "title": "Bug fix needed"},
        )

        assert payload.issue["number"] == 42

    def test_payload_with_pull_request(self):
        """Test payload with PR data."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
            pull_request={"number": 123, "title": "Add new feature"},
        )

        assert payload.pull_request["number"] == 123

    def test_get_owner(self):
        """Test extracting owner from repository."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
        )

        assert payload.get_owner() == "test-owner"

    def test_get_repo_name(self):
        """Test extracting repo name from repository."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
        )

        assert payload.get_repo_name() == "test-repo"

    def test_get_full_repo_name(self):
        """Test getting full repo name (owner/repo)."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
        )

        assert payload.get_full_repo_name() == "test-owner/test-repo"

    def test_get_comment_id(self):
        """Test extracting comment ID."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
            comment={"id": 12345, "body": "test"},
        )

        assert payload.get_comment_id() == 12345

    def test_get_comment_id_none_when_no_comment(self):
        """Test comment ID is None when no comment."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
        )

        assert payload.get_comment_id() is None

    def test_get_issue_number_from_issue(self):
        """Test extracting issue number from issue."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
            issue={"number": 42},
        )

        assert payload.get_issue_or_pr_number() == 42

    def test_get_issue_number_from_pr(self):
        """Test extracting number from PR when no issue."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
            pull_request={"number": 123},
        )

        assert payload.get_issue_or_pr_number() == 123

    def test_allows_extra_fields(self):
        """Test that extra fields are allowed."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
            sender={"login": "user123"},  # Extra field
            action="created",  # Extra field
        )

        assert payload.sender["login"] == "user123"
        assert payload.action == "created"

    def test_user_content_extraction(self):
        """Test user content field."""
        from domain.models import GitHubWebhookPayload

        payload = GitHubWebhookPayload(
            repository={"name": "test-repo", "owner": {"login": "test-owner"}},
            user_content="Please review this code",
        )

        assert payload.user_content == "Please review this code"


# =============================================================================
# TEST: Jira Webhook Payload
# =============================================================================

class TestJiraWebhookPayload:
    """Tests for JiraWebhookPayload model."""

    def test_minimal_payload(self):
        """Test creating payload with minimal data."""
        from domain.models import JiraWebhookPayload

        payload = JiraWebhookPayload(
            issue={"key": "TEST-123", "fields": {"summary": "Test issue"}},
        )

        assert payload.issue["key"] == "TEST-123"

    def test_get_ticket_key(self):
        """Test extracting ticket key."""
        from domain.models import JiraWebhookPayload

        payload = JiraWebhookPayload(
            issue={"key": "PROJ-456", "fields": {"summary": "Bug"}},
        )

        assert payload.get_ticket_key() == "PROJ-456"

    def test_get_ticket_key_defaults_to_unknown(self):
        """Test ticket key defaults to 'unknown'."""
        from domain.models import JiraWebhookPayload

        payload = JiraWebhookPayload(issue={})

        assert payload.get_ticket_key() == "unknown"

    def test_payload_with_comment(self):
        """Test payload with comment."""
        from domain.models import JiraWebhookPayload

        payload = JiraWebhookPayload(
            issue={"key": "TEST-123"},
            comment={"body": "@agent implement this feature"},
        )

        assert payload.comment["body"] == "@agent implement this feature"

    def test_payload_with_changelog(self):
        """Test payload with changelog."""
        from domain.models import JiraWebhookPayload

        payload = JiraWebhookPayload(
            issue={"key": "TEST-123"},
            changelog={"items": [{"field": "assignee", "toString": "AI Agent"}]},
        )

        assert payload.changelog["items"][0]["field"] == "assignee"

    def test_get_user_request_from_user_content(self):
        """Test extracting user request from user_content field."""
        from domain.models import JiraWebhookPayload

        payload = JiraWebhookPayload(
            issue={"key": "TEST-123"},
            user_content="implement the login feature",
        )

        assert payload.get_user_request() == "implement the login feature"

    def test_allows_extra_fields(self):
        """Test that extra fields are allowed."""
        from domain.models import JiraWebhookPayload

        payload = JiraWebhookPayload(
            issue={"key": "TEST-123"},
            webhookEvent="jira:issue_updated",  # Extra field
            user={"displayName": "John Doe"},  # Extra field
        )

        assert payload.webhookEvent == "jira:issue_updated"


# =============================================================================
# TEST: Slack Webhook Payload
# =============================================================================

class TestSlackWebhookPayload:
    """Tests for SlackWebhookPayload model."""

    def test_minimal_payload(self):
        """Test creating payload with minimal data."""
        from domain.models import SlackWebhookPayload

        payload = SlackWebhookPayload(
            event={"type": "message", "text": "@agent help"},
        )

        assert payload.event["type"] == "message"

    def test_get_channel(self):
        """Test extracting channel."""
        from domain.models import SlackWebhookPayload

        payload = SlackWebhookPayload(
            event={"type": "message", "channel": "C12345"},
        )

        assert payload.get_channel() == "C12345"

    def test_get_thread_ts(self):
        """Test extracting thread timestamp."""
        from domain.models import SlackWebhookPayload

        payload = SlackWebhookPayload(
            event={"type": "message", "ts": "1234567890.123456"},
        )

        assert payload.get_thread_ts() == "1234567890.123456"

    def test_get_text(self):
        """Test extracting message text."""
        from domain.models import SlackWebhookPayload

        payload = SlackWebhookPayload(
            event={"type": "message", "text": "@agent review the code"},
        )

        assert payload.get_text() == "@agent review the code"

    def test_allows_extra_fields(self):
        """Test that extra fields are allowed."""
        from domain.models import SlackWebhookPayload

        payload = SlackWebhookPayload(
            event={"type": "message"},
            type="event_callback",  # Extra field
            team_id="T12345",  # Extra field
        )

        assert payload.type == "event_callback"


# =============================================================================
# TEST: Routing Metadata
# =============================================================================

class TestRoutingMetadata:
    """Tests for RoutingMetadata model."""

    def test_empty_routing(self):
        """Test creating empty routing metadata."""
        from domain.models import RoutingMetadata

        routing = RoutingMetadata()

        assert routing.repo is None
        assert routing.pr_number is None
        assert routing.ticket_key is None
        assert routing.slack_channel is None

    def test_github_routing(self):
        """Test GitHub-specific routing."""
        from domain.models import RoutingMetadata

        routing = RoutingMetadata(
            repo="owner/repo",
            pr_number=123,
        )

        assert routing.repo == "owner/repo"
        assert routing.pr_number == 123

    def test_jira_routing(self):
        """Test Jira-specific routing."""
        from domain.models import RoutingMetadata

        routing = RoutingMetadata(
            ticket_key="PROJ-456",
        )

        assert routing.ticket_key == "PROJ-456"

    def test_slack_routing(self):
        """Test Slack-specific routing."""
        from domain.models import RoutingMetadata

        routing = RoutingMetadata(
            slack_channel="C12345",
            slack_thread_ts="1234567890.123456",
        )

        assert routing.slack_channel == "C12345"
        assert routing.slack_thread_ts == "1234567890.123456"

    def test_pr_number_validation_positive(self):
        """Test PR number must be positive."""
        from domain.models import RoutingMetadata
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RoutingMetadata(pr_number=-1)

    def test_pr_number_validation_zero(self):
        """Test PR number cannot be zero."""
        from domain.models import RoutingMetadata
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RoutingMetadata(pr_number=0)


class TestPRRouting:
    """Tests for PRRouting model (required fields)."""

    def test_required_fields(self):
        """Test PR routing requires repo and pr_number."""
        from domain.models import PRRouting
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PRRouting()  # Missing required fields

    def test_valid_pr_routing(self):
        """Test valid PR routing."""
        from domain.models import PRRouting

        routing = PRRouting(repo="owner/repo", pr_number=123)

        assert routing.repo == "owner/repo"
        assert routing.pr_number == 123

    def test_pr_number_must_be_positive(self):
        """Test PR number validation."""
        from domain.models import PRRouting
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PRRouting(repo="owner/repo", pr_number=0)


# =============================================================================
# TEST: Task Completion Context
# =============================================================================

class TestTaskCompletionContext:
    """Tests for TaskCompletionContext model."""

    def test_minimal_context(self):
        """Test creating minimal task completion context."""
        from domain.models import TaskCompletionContext, WebhookSource

        ctx = TaskCompletionContext(
            payload={"repository": {"name": "test"}},
            message="Task completed successfully",
            success=True,
        )

        assert ctx.message == "Task completed successfully"
        assert ctx.success is True
        assert ctx.task_id is None
        assert ctx.cost_usd == 0.0

    def test_full_context(self):
        """Test creating full task completion context."""
        from domain.models import TaskCompletionContext, WebhookSource

        ctx = TaskCompletionContext(
            payload={"repository": {"name": "test"}},
            message="Task completed successfully",
            success=True,
            cost_usd=0.05,
            task_id="task-abc123",
            command="review",
            result="Review completed with 3 suggestions",
            error=None,
            source=WebhookSource.GITHUB,
        )

        assert ctx.task_id == "task-abc123"
        assert ctx.command == "review"
        assert ctx.cost_usd == 0.05
        assert ctx.source == WebhookSource.GITHUB

    def test_failed_context(self):
        """Test task completion context for failed task."""
        from domain.models import TaskCompletionContext

        ctx = TaskCompletionContext(
            payload={},
            message="❌",
            success=False,
            error="Rate limit exceeded",
        )

        assert ctx.success is False
        assert ctx.error == "Rate limit exceeded"

    def test_cost_validation(self):
        """Test cost cannot be negative."""
        from domain.models import TaskCompletionContext
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TaskCompletionContext(
                payload={},
                message="Test",
                success=True,
                cost_usd=-0.01,
            )

    def test_has_meaningful_response_with_result(self):
        """Test has_meaningful_response with substantial result."""
        from domain.models import TaskCompletionContext

        ctx = TaskCompletionContext(
            payload={},
            message="Task done",
            success=True,
            result="This is a substantial result with more than 50 characters to be meaningful.",
        )

        assert ctx.has_meaningful_response() is True

    def test_has_meaningful_response_with_message(self):
        """Test has_meaningful_response with substantial message."""
        from domain.models import TaskCompletionContext

        ctx = TaskCompletionContext(
            payload={},
            message="This is a substantial message with more than 50 characters to be meaningful.",
            success=True,
        )

        assert ctx.has_meaningful_response() is True

    def test_has_meaningful_response_empty(self):
        """Test has_meaningful_response with minimal content."""
        from domain.models import TaskCompletionContext

        ctx = TaskCompletionContext(
            payload={},
            message="❌",
            success=False,
        )

        assert ctx.has_meaningful_response() is False


# =============================================================================
# TEST: Task Completion Result
# =============================================================================

class TestTaskCompletionResult:
    """Tests for TaskCompletionResult model."""

    def test_successful_result(self):
        """Test creating successful completion result."""
        from domain.models import TaskCompletionResult

        result = TaskCompletionResult(
            comment_posted=True,
            notification_sent=True,
            comment_id=12345,
        )

        assert result.comment_posted is True
        assert result.notification_sent is True
        assert result.comment_id == 12345

    def test_failed_result(self):
        """Test creating failed completion result."""
        from domain.models import TaskCompletionResult

        result = TaskCompletionResult(
            comment_posted=False,
            notification_sent=True,
            error_reaction_added=True,
        )

        assert result.comment_posted is False
        assert result.error_reaction_added is True


# =============================================================================
# TEST: Task Summary
# =============================================================================

class TestTaskSummary:
    """Tests for TaskSummary model."""

    def test_minimal_summary(self):
        """Test creating minimal summary."""
        from domain.models import TaskSummary

        summary = TaskSummary(summary="Task completed successfully")

        assert summary.summary == "Task completed successfully"
        assert summary.classification == "SIMPLE"

    def test_full_summary(self):
        """Test creating full summary."""
        from domain.models import TaskSummary

        summary = TaskSummary(
            summary="Code review completed",
            classification="COMPLEX",
            what_was_done="Reviewed 15 files, found 3 issues",
            key_insights="Performance improvement suggestions included",
        )

        assert summary.classification == "COMPLEX"
        assert summary.what_was_done is not None


# =============================================================================
# TEST: Task Notification
# =============================================================================

class TestTaskNotification:
    """Tests for TaskNotification model."""

    def test_minimal_notification(self):
        """Test creating minimal notification."""
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=True,
        )

        assert notification.task_id == "task-123"
        assert notification.source == WebhookSource.GITHUB

    def test_notification_with_result(self):
        """Test notification with result."""
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.JIRA,
            command="implement",
            success=True,
            result="Feature implemented successfully",
            cost_usd=0.12,
        )

        assert notification.result == "Feature implemented successfully"
        assert notification.cost_usd == 0.12

    def test_notification_with_error(self):
        """Test notification with error."""
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.SLACK,
            command="help",
            success=False,
            error="API rate limit exceeded",
        )

        assert notification.success is False
        assert notification.error == "API rate limit exceeded"

    def test_get_channel_for_success(self):
        """Test getting appropriate channel for success."""
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=True,
        )

        assert notification.get_default_channel() == "#ai-agent-activity"

    def test_get_channel_for_failure(self):
        """Test getting appropriate channel for failure."""
        from domain.models import TaskNotification, WebhookSource

        notification = TaskNotification(
            task_id="task-123",
            source=WebhookSource.GITHUB,
            command="review",
            success=False,
        )

        assert notification.get_default_channel() == "#ai-agent-errors"


# =============================================================================
# TEST: Result Types
# =============================================================================

class TestResult:
    """Tests for Result types."""

    def test_success_creation(self):
        """Test creating Success result."""
        from domain.result import Success

        result = Success(value="Hello World")

        assert result.value == "Hello World"
        assert result.is_success() is True
        assert result.is_failure() is False

    def test_failure_creation(self):
        """Test creating Failure result."""
        from domain.result import Failure

        result = Failure(
            error="Something went wrong",
            error_type="RuntimeError",
        )

        assert result.error == "Something went wrong"
        assert result.error_type == "RuntimeError"
        assert result.is_success() is False
        assert result.is_failure() is True

    def test_failure_recoverable(self):
        """Test Failure with recoverable flag."""
        from domain.result import Failure

        result = Failure(
            error="Rate limit",
            error_type="RateLimitError",
            recoverable=True,
        )

        assert result.recoverable is True

    def test_failure_not_recoverable(self):
        """Test Failure with not recoverable."""
        from domain.result import Failure

        result = Failure(
            error="Token not configured",
            error_type="ConfigurationError",
            recoverable=False,
        )

        assert result.recoverable is False

    def test_success_unwrap(self):
        """Test unwrapping Success value."""
        from domain.result import Success

        result = Success(value=42)

        assert result.unwrap() == 42

    def test_failure_unwrap_raises(self):
        """Test unwrapping Failure raises error."""
        from domain.result import Failure

        result = Failure(error="Test error", error_type="TestError")

        with pytest.raises(ValueError, match="Cannot unwrap Failure"):
            result.unwrap()

    def test_success_unwrap_or(self):
        """Test unwrap_or with Success."""
        from domain.result import Success

        result = Success(value=42)

        assert result.unwrap_or(0) == 42

    def test_failure_unwrap_or(self):
        """Test unwrap_or with Failure."""
        from domain.result import Failure

        result = Failure(error="Error", error_type="E")

        assert result.unwrap_or(0) == 0

    def test_success_map(self):
        """Test mapping over Success."""
        from domain.result import Success

        result = Success(value=5)
        mapped = result.map(lambda x: x * 2)

        assert mapped.value == 10

    def test_failure_map(self):
        """Test mapping over Failure (should return same Failure)."""
        from domain.result import Failure

        result = Failure(error="Error", error_type="E")
        mapped = result.map(lambda x: x * 2)

        assert mapped.is_failure()
        assert mapped.error == "Error"
