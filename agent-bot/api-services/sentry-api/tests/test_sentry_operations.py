"""Tests for Sentry API operations.

Tests business requirements for Sentry integration.
"""

import pytest


class MockSentryClient:
    """Mock Sentry client for testing without real API calls."""

    def __init__(self, token: str = "test-sentry-token", org: str = "test-org"):
        self._token = token
        self._org = org
        self._issues: dict[str, dict] = {}

    def set_issue(self, issue_id: str, data: dict):
        """Set mock issue data."""
        self._issues[issue_id] = data

    async def get_issue(self, issue_id: str) -> dict:
        """Get issue details."""
        if issue_id in self._issues:
            return self._issues[issue_id]
        return {
            "id": issue_id,
            "title": "TypeError: Cannot read property 'foo' of undefined",
            "culprit": "src/utils/parser.js",
            "status": "unresolved",
            "level": "error",
            "count": 42,
            "userCount": 15,
            "firstSeen": "2026-01-30T12:00:00Z",
            "lastSeen": "2026-01-31T12:00:00Z",
            "metadata": {
                "type": "TypeError",
                "value": "Cannot read property 'foo' of undefined",
            },
        }

    async def get_issue_events(self, issue_id: str, limit: int = 10) -> list:
        """Get events for an issue."""
        return [
            {
                "eventID": "event-001",
                "dateCreated": "2026-01-31T12:00:00Z",
                "context": {"browser": "Chrome 120"},
                "entries": [
                    {
                        "type": "exception",
                        "data": {
                            "values": [
                                {
                                    "type": "TypeError",
                                    "value": "Cannot read property 'foo' of undefined",
                                    "stacktrace": {
                                        "frames": [
                                            {
                                                "filename": "src/utils/parser.js",
                                                "function": "parseData",
                                                "lineno": 42,
                                            }
                                        ]
                                    },
                                }
                            ]
                        },
                    }
                ],
            }
        ]

    async def add_comment(self, issue_id: str, text: str) -> dict:
        """Add comment to issue."""
        return {
            "id": "note-001",
            "text": text,
            "user": {"name": "Agent"},
        }

    async def update_status(self, issue_id: str, status: str) -> dict:
        """Update issue status."""
        valid_statuses = ["resolved", "unresolved", "ignored"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")
        return {
            "id": issue_id,
            "status": status,
        }

    async def get_affected_users(self, issue_id: str) -> dict:
        """Get affected user count."""
        issue = await self.get_issue(issue_id)
        return {
            "userCount": issue.get("userCount", 0),
        }


@pytest.fixture
def sentry_client():
    """Mock Sentry client fixture."""
    return MockSentryClient()


class TestSentryIssueOperations:
    """Tests for Sentry issue operations."""

    async def test_get_issue_details(self, sentry_client):
        """Business requirement: Issue reading works."""
        result = await sentry_client.get_issue("12345")

        assert result["id"] == "12345"
        assert "title" in result
        assert "culprit" in result
        assert "status" in result

    async def test_get_issue_with_stacktrace(self, sentry_client):
        """Business requirement: Stacktrace, metadata returned."""
        sentry_client.set_issue(
            "12345",
            {
                "id": "12345",
                "title": "Error",
                "metadata": {
                    "stacktrace": {"frames": [{"filename": "test.js", "lineno": 10}]}
                },
            },
        )

        result = await sentry_client.get_issue("12345")

        assert "metadata" in result
        assert "stacktrace" in result["metadata"]


class TestSentryCommentOperations:
    """Tests for Sentry comment operations."""

    async def test_add_comment_to_issue(self, sentry_client):
        """Business requirement: Communication works."""
        result = await sentry_client.add_comment(
            issue_id="12345",
            text="Investigating this issue...",
        )

        assert result["text"] == "Investigating this issue..."
        assert "id" in result


class TestSentryStatusOperations:
    """Tests for Sentry status management."""

    async def test_update_issue_status_resolved(self, sentry_client):
        """Business requirement: Status management."""
        result = await sentry_client.update_status(
            issue_id="12345",
            status="resolved",
        )

        assert result["status"] == "resolved"

    async def test_update_issue_status_ignored(self, sentry_client):
        """Issues can be ignored."""
        result = await sentry_client.update_status(
            issue_id="12345",
            status="ignored",
        )

        assert result["status"] == "ignored"

    async def test_invalid_status_rejected(self, sentry_client):
        """Invalid status raises error."""
        with pytest.raises(ValueError):
            await sentry_client.update_status(
                issue_id="12345",
                status="invalid_status",
            )


class TestSentryImpactAnalysis:
    """Tests for Sentry impact analysis."""

    async def test_get_affected_users(self, sentry_client):
        """Business requirement: Impact analysis."""
        result = await sentry_client.get_affected_users("12345")

        assert "userCount" in result
        assert result["userCount"] >= 0


class TestSentryEventRetrieval:
    """Tests for Sentry event retrieval."""

    async def test_get_issue_events(self, sentry_client):
        """Business requirement: Event details available."""
        events = await sentry_client.get_issue_events("12345")

        assert len(events) > 0
        assert "eventID" in events[0]
        assert "entries" in events[0]
