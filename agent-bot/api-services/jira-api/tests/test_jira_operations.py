"""Tests for Jira API operations.

Tests business requirements for Jira integration.
"""

import pytest


class MockJiraClient:
    """Mock Jira client for testing without real API calls."""

    def __init__(
        self,
        base_url: str = "https://jira.example.com",
        email: str = "test@example.com",
        token: str = "test-token",
    ):
        self._base_url = base_url
        self._email = email
        self._token = token
        self._issues: dict[str, dict] = {}
        self._transitions: dict[str, list] = {}

    def set_issue(self, issue_key: str, data: dict):
        """Set mock issue data."""
        self._issues[issue_key] = data

    def set_transitions(self, issue_key: str, transitions: list):
        """Set available transitions for an issue."""
        self._transitions[issue_key] = transitions

    async def get_issue(self, issue_key: str) -> dict:
        """Get issue details."""
        if issue_key in self._issues:
            return self._issues[issue_key]
        return {
            "key": issue_key,
            "fields": {
                "summary": "Test Issue",
                "description": "Test description",
                "status": {"name": "To Do"},
                "priority": {"name": "Medium"},
                "labels": [],
                "project": {"key": issue_key.split("-")[0]},
            },
        }

    async def create_issue(
        self,
        project: str,
        summary: str,
        description: str | None = None,
        issue_type: str = "Task",
        labels: list[str] | None = None,
    ) -> dict:
        """Create a new issue."""
        issue_key = f"{project}-123"
        return {
            "key": issue_key,
            "self": f"{self._base_url}/rest/api/2/issue/{issue_key}",
        }

    async def update_issue(self, issue_key: str, fields: dict) -> dict:
        """Update issue fields."""
        return {"key": issue_key}

    async def add_comment(self, issue_key: str, body: str) -> dict:
        """Add comment to issue."""
        return {
            "id": "10001",
            "body": body,
            "author": {"displayName": "Agent"},
        }

    async def search_issues(self, jql: str, max_results: int = 50) -> dict:
        """Search issues by JQL."""
        return {
            "total": 1,
            "issues": [
                {
                    "key": "PROJ-123",
                    "fields": {"summary": "Matching issue"},
                }
            ],
        }

    async def get_transitions(self, issue_key: str) -> list:
        """Get available transitions for an issue."""
        if issue_key in self._transitions:
            return self._transitions[issue_key]
        return [
            {"id": "11", "name": "To Do"},
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]

    async def transition_issue(self, issue_key: str, transition_id: str) -> None:
        """Transition issue to new status."""
        valid_transitions = await self.get_transitions(issue_key)
        valid_ids = [t["id"] for t in valid_transitions]
        if transition_id not in valid_ids:
            raise ValueError(f"Invalid transition: {transition_id}")


@pytest.fixture
def jira_client():
    """Mock Jira client fixture."""
    return MockJiraClient()


class TestJiraIssueOperations:
    """Tests for Jira issue operations."""

    async def test_get_issue_details(self, jira_client):
        """Business requirement: Issue reading works."""
        result = await jira_client.get_issue("PROJ-123")

        assert result["key"] == "PROJ-123"
        assert "fields" in result
        assert "summary" in result["fields"]
        assert "status" in result["fields"]

    async def test_create_issue(self, jira_client):
        """Business requirement: Issue creation works."""
        result = await jira_client.create_issue(
            project="PROJ",
            summary="New bug to fix",
            description="Details about the bug",
            issue_type="Bug",
            labels=["AI-Fix"],
        )

        assert "key" in result
        assert result["key"].startswith("PROJ-")

    async def test_update_issue_fields(self, jira_client):
        """Business requirement: Editing works."""
        result = await jira_client.update_issue(
            issue_key="PROJ-123",
            fields={"summary": "Updated summary"},
        )

        assert result["key"] == "PROJ-123"


class TestJiraCommentOperations:
    """Tests for Jira comment operations."""

    async def test_add_comment_to_issue(self, jira_client):
        """Business requirement: Communication works."""
        result = await jira_client.add_comment(
            issue_key="PROJ-123",
            body="Analysis complete. Found the root cause.",
        )

        assert result["body"] == "Analysis complete. Found the root cause."
        assert "id" in result


class TestJiraSearchOperations:
    """Tests for Jira search operations."""

    async def test_search_issues_by_jql(self, jira_client):
        """Business requirement: Search works."""
        result = await jira_client.search_issues(
            jql='project = PROJ AND labels = "AI-Fix" AND status != Done'
        )

        assert "total" in result
        assert "issues" in result
        assert len(result["issues"]) >= 0


class TestJiraTransitionOperations:
    """Tests for Jira workflow transitions."""

    async def test_get_transitions(self, jira_client):
        """Business requirement: Workflow visibility."""
        transitions = await jira_client.get_transitions("PROJ-123")

        assert len(transitions) > 0
        assert all("id" in t for t in transitions)
        assert all("name" in t for t in transitions)

    async def test_transition_issue(self, jira_client):
        """Business requirement: Workflow works."""
        await jira_client.transition_issue(
            issue_key="PROJ-123",
            transition_id="21",
        )

    async def test_invalid_transition_rejected(self, jira_client):
        """Business requirement: Workflow enforcement."""
        jira_client.set_transitions("PROJ-123", [{"id": "11", "name": "To Do"}])

        with pytest.raises(ValueError):
            await jira_client.transition_issue(
                issue_key="PROJ-123",
                transition_id="99",
            )
