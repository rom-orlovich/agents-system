"""Sentry webhook payload fixtures for testing."""

from typing import Any


def sentry_issue_created_payload(
    issue_id: str = "12345",
    title: str = "TypeError: Cannot read property 'foo' of undefined",
    culprit: str = "src/utils/parser.js",
    level: str = "error",
    platform: str = "javascript",
    project: str = "test-project",
    first_seen: str = "2026-01-31T12:00:00Z",
    count: int = 1,
    user_count: int = 1,
) -> dict[str, Any]:
    """Create a Sentry issue created payload."""
    return {
        "action": "created",
        "data": {
            "issue": {
                "id": issue_id,
                "title": title,
                "culprit": culprit,
                "shortId": f"{project.upper()}-{issue_id}",
                "level": level,
                "platform": platform,
                "project": {
                    "id": "10001",
                    "name": project,
                    "slug": project,
                },
                "status": "unresolved",
                "firstSeen": first_seen,
                "lastSeen": first_seen,
                "count": str(count),
                "userCount": user_count,
                "metadata": {
                    "type": "TypeError",
                    "value": "Cannot read property 'foo' of undefined",
                    "filename": culprit,
                },
            },
        },
        "installation": {
            "uuid": "installation-uuid-123",
        },
        "actor": {
            "type": "application",
            "id": "sentry",
            "name": "Sentry",
        },
    }


def sentry_issue_regression_payload(
    issue_id: str = "12345",
    title: str = "TypeError: Cannot read property 'foo' of undefined",
    culprit: str = "src/utils/parser.js",
    project: str = "test-project",
    count: int = 100,
    user_count: int = 50,
) -> dict[str, Any]:
    """Create a Sentry issue regression payload (high priority)."""
    payload = sentry_issue_created_payload(
        issue_id=issue_id,
        title=title,
        culprit=culprit,
        project=project,
        count=count,
        user_count=user_count,
    )
    payload["action"] = "regression"
    payload["data"]["issue"]["status"] = "unresolved"
    payload["data"]["issue"]["substatus"] = "regressed"
    payload["data"]["issue"]["isRegression"] = True
    return payload


def sentry_issue_resolved_payload(
    issue_id: str = "12345",
    title: str = "TypeError: Cannot read property 'foo' of undefined",
    project: str = "test-project",
    resolved_by: str = "testuser",
) -> dict[str, Any]:
    """Create a Sentry issue resolved payload (should be ignored)."""
    payload = sentry_issue_created_payload(
        issue_id=issue_id,
        title=title,
        project=project,
    )
    payload["action"] = "resolved"
    payload["data"]["issue"]["status"] = "resolved"
    payload["data"]["issue"]["resolvedBy"] = {
        "type": "user",
        "id": resolved_by,
        "name": resolved_by,
    }
    return payload


def sentry_issue_with_stacktrace_payload(
    issue_id: str = "12345",
    title: str = "TypeError: Cannot read property 'foo' of undefined",
    project: str = "test-project",
) -> dict[str, Any]:
    """Create a Sentry payload with full stacktrace for error context."""
    payload = sentry_issue_created_payload(
        issue_id=issue_id,
        title=title,
        project=project,
    )
    payload["data"]["issue"]["metadata"]["stacktrace"] = {
        "frames": [
            {
                "filename": "src/utils/parser.js",
                "function": "parseData",
                "lineno": 42,
                "colno": 15,
                "context_line": "    const result = data.foo.bar;",
                "pre_context": [
                    "function parseData(data) {",
                    "    // Parse incoming data",
                ],
                "post_context": [
                    "    return result;",
                    "}",
                ],
            },
            {
                "filename": "src/handlers/main.js",
                "function": "handleRequest",
                "lineno": 15,
                "colno": 10,
                "context_line": "    const parsed = parseData(request.body);",
            },
        ],
    }
    return payload
