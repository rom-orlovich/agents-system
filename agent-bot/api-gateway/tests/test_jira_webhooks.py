"""Tests for Jira webhook business logic.

Tests processing of Jira webhook events with AI-Fix label filtering.
"""

from .fixtures import (
    jira_issue_created_payload,
    jira_issue_updated_payload,
    jira_comment_created_payload,
)


AI_FIX_LABEL = "AI-Fix"


def has_ai_fix_label(payload: dict) -> bool:
    """Check if payload has AI-Fix label."""
    labels = payload.get("issue", {}).get("fields", {}).get("labels", [])
    return AI_FIX_LABEL in labels


def should_process_jira_event(event_type: str, payload: dict) -> bool:
    """Determine if Jira event should be processed."""
    supported_events = ["jira:issue_created", "jira:issue_updated", "comment_created"]

    if event_type not in supported_events:
        return False

    return has_ai_fix_label(payload)


def extract_jira_task_info(event_type: str, payload: dict) -> dict:
    """Extract task info from Jira webhook payload."""
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})

    task_info = {
        "source": "jira",
        "event_type": event_type,
        "issue_key": issue.get("key"),
        "project": fields.get("project", {}).get("key"),
        "summary": fields.get("summary"),
        "description": fields.get("description"),
        "labels": fields.get("labels", []),
        "issue_type": fields.get("issuetype", {}).get("name"),
        "priority": fields.get("priority", {}).get("name"),
        "status": fields.get("status", {}).get("name"),
    }

    if event_type == "comment_created":
        comment = payload.get("comment", {})
        task_info["comment"] = {
            "id": comment.get("id"),
            "body": comment.get("body"),
            "author": comment.get("author", {}).get("displayName"),
        }

    return task_info


class TestJiraLabelFiltering:
    """Tests for AI-Fix label requirement."""

    def test_issue_created_with_ai_fix_label_processed(self):
        """Business requirement: AI-Fix label required."""
        payload = jira_issue_created_payload(labels=["AI-Fix", "bug"])

        assert should_process_jira_event("jira:issue_created", payload) is True

    def test_issue_created_without_ai_fix_ignored(self):
        """Business requirement: Only AI-Fix processed."""
        payload = jira_issue_created_payload(labels=["bug", "urgent"])

        assert should_process_jira_event("jira:issue_created", payload) is False

    def test_issue_updated_with_ai_fix_label_processed(self):
        """Business requirement: Label added later works."""
        payload = jira_issue_updated_payload(labels=["AI-Fix"])

        assert should_process_jira_event("jira:issue_updated", payload) is True

    def test_comment_on_ai_fix_issue_processed(self):
        """Business requirement: Comments extend conversation."""
        payload = jira_comment_created_payload(issue_key="PROJ-123")
        payload["issue"]["fields"] = {"labels": ["AI-Fix"]}

        assert should_process_jira_event("comment_created", payload) is True

    def test_comment_on_non_ai_fix_issue_ignored(self):
        """Business requirement: Only AI-Fix issue comments."""
        payload = jira_comment_created_payload(issue_key="PROJ-123")
        payload["issue"]["fields"] = {"labels": ["bug"]}

        assert should_process_jira_event("comment_created", payload) is False

    def test_empty_labels_ignored(self):
        """Business requirement: No labels means no processing."""
        payload = jira_issue_created_payload(labels=[])

        assert should_process_jira_event("jira:issue_created", payload) is False


class TestJiraTaskExtraction:
    """Tests for extracting task info from Jira payloads."""

    def test_issue_created_extracts_all_fields(self):
        """Business requirement: Context preserved."""
        payload = jira_issue_created_payload(
            issue_key="PROJ-123",
            summary="Fix authentication bug",
            description="Users can't log in via SSO",
            labels=["AI-Fix", "bug"],
            project="PROJ",
            issue_type="Bug",
            priority="High",
        )

        task_info = extract_jira_task_info("jira:issue_created", payload)

        assert task_info["source"] == "jira"
        assert task_info["event_type"] == "jira:issue_created"
        assert task_info["issue_key"] == "PROJ-123"
        assert task_info["project"] == "PROJ"
        assert task_info["summary"] == "Fix authentication bug"
        assert "AI-Fix" in task_info["labels"]

    def test_comment_extracts_comment_info(self):
        """Business requirement: Comment details preserved."""
        payload = jira_comment_created_payload(
            issue_key="PROJ-123",
            comment_id="10001",
            body="Please prioritize this fix",
            author="reviewer",
        )
        payload["issue"]["fields"] = {"labels": ["AI-Fix"]}

        task_info = extract_jira_task_info("comment_created", payload)

        assert task_info["comment"]["id"] == "10001"
        assert task_info["comment"]["body"] == "Please prioritize this fix"
        assert task_info["comment"]["author"] == "reviewer"


class TestJiraEventTypes:
    """Tests for supported Jira event types."""

    def test_supported_jira_events(self):
        """Verify all supported Jira events."""
        payload_with_label = jira_issue_created_payload(labels=["AI-Fix"])

        supported = ["jira:issue_created", "jira:issue_updated", "comment_created"]
        for event in supported:
            assert should_process_jira_event(event, payload_with_label) is True

    def test_unsupported_jira_events(self):
        """Verify unsupported events are ignored."""
        payload = jira_issue_created_payload(labels=["AI-Fix"])

        unsupported = [
            "jira:issue_deleted",
            "jira:worklog_created",
            "sprint:started",
        ]
        for event in unsupported:
            assert should_process_jira_event(event, payload) is False


class TestAIFixLabelRequirement:
    """Tests for AI-Fix label business requirement."""

    def test_ai_fix_label_case_sensitive(self):
        """AI-Fix label matching is case-sensitive."""
        payload_correct = jira_issue_created_payload(labels=["AI-Fix"])
        payload_wrong_case = jira_issue_created_payload(labels=["ai-fix"])
        payload_different = jira_issue_created_payload(labels=["AIFix"])

        assert should_process_jira_event("jira:issue_created", payload_correct) is True
        assert (
            should_process_jira_event("jira:issue_created", payload_wrong_case) is False
        )
        assert (
            should_process_jira_event("jira:issue_created", payload_different) is False
        )

    def test_ai_fix_with_other_labels(self):
        """AI-Fix can coexist with other labels."""
        payload = jira_issue_created_payload(
            labels=["bug", "AI-Fix", "urgent", "backend"]
        )

        assert should_process_jira_event("jira:issue_created", payload) is True
        assert has_ai_fix_label(payload) is True
