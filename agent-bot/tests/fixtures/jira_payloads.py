"""Jira webhook payload fixtures for testing."""

from typing import Any


def jira_issue_created_payload(
    issue_key: str = "PROJ-123",
    summary: str = "Test Issue",
    description: str = "Test description",
    labels: list[str] | None = None,
    project: str = "PROJ",
    issue_type: str = "Bug",
    priority: str = "Medium",
    reporter: str = "testuser",
) -> dict[str, Any]:
    """Create a Jira issue created payload."""
    return {
        "webhookEvent": "jira:issue_created",
        "timestamp": 1706702400000,
        "issue": {
            "id": "10001",
            "key": issue_key,
            "self": f"https://jira.example.com/rest/api/2/issue/{issue_key}",
            "fields": {
                "summary": summary,
                "description": description,
                "labels": labels or [],
                "project": {
                    "key": project,
                    "name": f"{project} Project",
                },
                "issuetype": {
                    "name": issue_type,
                },
                "priority": {
                    "name": priority,
                },
                "reporter": {
                    "displayName": reporter,
                    "emailAddress": f"{reporter}@example.com",
                },
                "status": {
                    "name": "To Do",
                },
                "created": "2026-01-31T12:00:00.000+0000",
                "updated": "2026-01-31T12:00:00.000+0000",
            },
        },
        "user": {
            "displayName": reporter,
            "emailAddress": f"{reporter}@example.com",
        },
    }


def jira_issue_updated_payload(
    issue_key: str = "PROJ-123",
    summary: str = "Updated Issue",
    labels: list[str] | None = None,
    project: str = "PROJ",
    change_type: str = "labels",
    from_value: str = "",
    to_value: str = "AI-Fix",
) -> dict[str, Any]:
    """Create a Jira issue updated payload."""
    payload = jira_issue_created_payload(
        issue_key=issue_key,
        summary=summary,
        labels=labels,
        project=project,
    )
    payload["webhookEvent"] = "jira:issue_updated"
    payload["changelog"] = {
        "id": "10001",
        "items": [
            {
                "field": change_type,
                "fieldtype": "jira",
                "from": from_value,
                "fromString": from_value,
                "to": to_value,
                "toString": to_value,
            }
        ],
    }
    return payload


def jira_comment_created_payload(
    issue_key: str = "PROJ-123",
    comment_id: str = "10001",
    body: str = "Test comment",
    author: str = "testuser",
) -> dict[str, Any]:
    """Create a Jira comment created payload."""
    return {
        "webhookEvent": "comment_created",
        "timestamp": 1706702400000,
        "issue": {
            "id": "10001",
            "key": issue_key,
            "self": f"https://jira.example.com/rest/api/2/issue/{issue_key}",
            "fields": {
                "summary": "Test Issue",
                "labels": ["AI-Fix"],
                "project": {
                    "key": "PROJ",
                },
            },
        },
        "comment": {
            "id": comment_id,
            "body": body,
            "author": {
                "displayName": author,
                "emailAddress": f"{author}@example.com",
            },
            "created": "2026-01-31T12:00:00.000+0000",
            "updated": "2026-01-31T12:00:00.000+0000",
        },
    }
