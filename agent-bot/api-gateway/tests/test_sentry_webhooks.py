"""Tests for Sentry webhook business logic.

Tests processing of Sentry error alerts.
"""

from .fixtures import (
    sentry_issue_created_payload,
    sentry_issue_regression_payload,
    sentry_issue_resolved_payload,
)


def should_process_sentry_event(payload: dict) -> bool:
    """Determine if Sentry event should be processed."""
    action = payload.get("action")
    return action in ["created", "regression"]


def get_sentry_priority(payload: dict) -> str:
    """Determine priority based on Sentry event type."""
    action = payload.get("action")
    if action == "regression":
        return "high"
    return "normal"


def extract_sentry_task_info(payload: dict) -> dict:
    """Extract task info from Sentry payload."""
    issue = payload.get("data", {}).get("issue", {})
    metadata = issue.get("metadata", {})

    task_info = {
        "source": "sentry",
        "action": payload.get("action"),
        "priority": get_sentry_priority(payload),
        "issue_id": issue.get("id"),
        "title": issue.get("title"),
        "culprit": issue.get("culprit"),
        "level": issue.get("level"),
        "platform": issue.get("platform"),
        "project": issue.get("project", {}).get("name"),
        "status": issue.get("status"),
        "first_seen": issue.get("firstSeen"),
        "count": issue.get("count"),
        "user_count": issue.get("userCount"),
        "error_type": metadata.get("type"),
        "error_value": metadata.get("value"),
    }

    if "stacktrace" in metadata:
        task_info["stacktrace"] = metadata["stacktrace"]

    return task_info


class TestSentryEventFiltering:
    """Tests for Sentry event filtering."""

    def test_new_error_creates_task(self):
        """Business requirement: Errors trigger investigation."""
        payload = sentry_issue_created_payload()
        assert should_process_sentry_event(payload) is True

    def test_regression_creates_task(self):
        """Business requirement: Regressions trigger task."""
        payload = sentry_issue_regression_payload()
        assert should_process_sentry_event(payload) is True

    def test_resolved_event_ignored(self):
        """Business requirement: Only active errors."""
        payload = sentry_issue_resolved_payload()
        assert should_process_sentry_event(payload) is False


class TestSentryPriority:
    """Tests for Sentry priority assignment."""

    def test_regression_creates_high_priority_task(self):
        """Business requirement: Regressions urgent."""
        payload = sentry_issue_regression_payload()
        priority = get_sentry_priority(payload)
        assert priority == "high"

    def test_new_issue_creates_normal_priority(self):
        """Business requirement: New issues have normal priority."""
        payload = sentry_issue_created_payload()
        priority = get_sentry_priority(payload)
        assert priority == "normal"


class TestSentryTaskExtraction:
    """Tests for extracting task info from Sentry payloads."""

    def test_task_contains_error_context(self):
        """Business requirement: Debug info preserved."""
        payload = sentry_issue_created_payload(
            issue_id="12345",
            title="TypeError: Cannot read property 'foo' of undefined",
            culprit="src/utils/parser.js",
            project="my-project",
            count=10,
            user_count=5,
        )

        task_info = extract_sentry_task_info(payload)

        assert task_info["source"] == "sentry"
        assert task_info["issue_id"] == "12345"
        assert (
            task_info["title"] == "TypeError: Cannot read property 'foo' of undefined"
        )
        assert task_info["culprit"] == "src/utils/parser.js"
        assert task_info["project"] == "my-project"
        assert task_info["user_count"] == 5

    def test_regression_has_high_priority(self):
        """Business requirement: Regression priority."""
        payload = sentry_issue_regression_payload()

        task_info = extract_sentry_task_info(payload)

        assert task_info["priority"] == "high"
        assert task_info["action"] == "regression"

    def test_error_metadata_extracted(self):
        """Business requirement: Error type and value extracted."""
        payload = sentry_issue_created_payload()

        task_info = extract_sentry_task_info(payload)

        assert task_info["error_type"] == "TypeError"
        assert "undefined" in task_info["error_value"]


class TestSentryEventTypes:
    """Tests for Sentry event type handling."""

    def test_created_action_processed(self):
        """Created action is processed."""
        payload = sentry_issue_created_payload()
        assert should_process_sentry_event(payload) is True
        assert payload["action"] == "created"

    def test_regression_action_processed(self):
        """Regression action is processed."""
        payload = sentry_issue_regression_payload()
        assert should_process_sentry_event(payload) is True
        assert payload["action"] == "regression"

    def test_resolved_action_not_processed(self):
        """Resolved action is not processed."""
        payload = sentry_issue_resolved_payload()
        assert should_process_sentry_event(payload) is False
        assert payload["action"] == "resolved"
