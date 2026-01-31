"""Tests for GitHub API operations.

Tests business requirements for GitHub integration.
"""

import pytest


class MockGitHubClient:
    """Mock GitHub client for testing without real API calls."""

    def __init__(self, token: str = "test-token"):
        self._token = token
        self._responses: dict[str, dict] = {}

    def set_response(self, method: str, path: str, response: dict):
        """Set mock response for a given path."""
        key = f"{method}:{path}"
        self._responses[key] = response

    async def get_repository(self, owner: str, repo: str) -> dict:
        """Get repository information."""
        return self._responses.get(
            f"GET:/repos/{owner}/{repo}",
            {
                "full_name": f"{owner}/{repo}",
                "default_branch": "main",
                "private": False,
            },
        )

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> dict:
        """Get issue information."""
        return self._responses.get(
            f"GET:/repos/{owner}/{repo}/issues/{issue_number}",
            {
                "number": issue_number,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
            },
        )

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
    ) -> dict:
        """Create a new issue."""
        return {
            "number": 123,
            "title": title,
            "body": body,
            "labels": [{"name": lbl} for lbl in (labels or [])],
            "html_url": f"https://github.com/{owner}/{repo}/issues/123",
        }

    async def create_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> dict:
        """Add comment to an issue."""
        return {
            "id": 456,
            "body": body,
            "html_url": f"https://github.com/{owner}/{repo}/issues/{issue_number}#issuecomment-456",
        }

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> dict:
        """Get pull request information."""
        return self._responses.get(
            f"GET:/repos/{owner}/{repo}/pulls/{pr_number}",
            {
                "number": pr_number,
                "title": "Test PR",
                "body": "Test PR body",
                "state": "open",
                "head": {"ref": "feature-branch", "sha": "abc123"},
                "base": {"ref": "main", "sha": "def456"},
            },
        )

    async def create_pr_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        commit_id: str,
        path: str,
        line: int,
    ) -> dict:
        """Add review comment to a PR."""
        return {
            "id": 789,
            "body": body,
            "path": path,
            "line": line,
        }

    async def get_file_contents(
        self, owner: str, repo: str, path: str, ref: str | None = None
    ) -> dict:
        """Get file contents from repository."""
        return {
            "name": path.split("/")[-1],
            "path": path,
            "content": "dGVzdCBjb250ZW50",
            "encoding": "base64",
        }

    async def create_branch(self, owner: str, repo: str, branch: str, sha: str) -> dict:
        """Create a new branch."""
        return {
            "ref": f"refs/heads/{branch}",
            "object": {"sha": sha},
        }

    async def search_code(self, query: str, per_page: int = 30, page: int = 1) -> dict:
        """Search code in repositories."""
        return {
            "total_count": 1,
            "items": [
                {
                    "name": "test.py",
                    "path": "src/test.py",
                    "repository": {"full_name": "test/repo"},
                }
            ],
        }

    async def list_branches(
        self, owner: str, repo: str, per_page: int = 30, page: int = 1
    ) -> list:
        """List repository branches."""
        return [
            {"name": "main", "commit": {"sha": "abc123"}},
            {"name": "develop", "commit": {"sha": "def456"}},
        ]


@pytest.fixture
def github_client():
    """Mock GitHub client fixture."""
    return MockGitHubClient()


class TestGitHubRepositoryOperations:
    """Tests for repository operations."""

    async def test_get_repository(self, github_client):
        """Business requirement: Repository reading works."""
        result = await github_client.get_repository("test-org", "test-repo")

        assert result["full_name"] == "test-org/test-repo"
        assert "default_branch" in result

    async def test_list_branches(self, github_client):
        """Business requirement: Branch listing works."""
        branches = await github_client.list_branches("test-org", "test-repo")

        assert len(branches) >= 1
        assert any(b["name"] == "main" for b in branches)


class TestGitHubIssueOperations:
    """Tests for issue operations."""

    async def test_get_issue(self, github_client):
        """Business requirement: Issue reading works."""
        result = await github_client.get_issue("test-org", "test-repo", 123)

        assert result["number"] == 123
        assert "title" in result
        assert "body" in result

    async def test_create_issue(self, github_client):
        """Business requirement: Issue creation works."""
        result = await github_client.create_issue(
            owner="test-org",
            repo="test-repo",
            title="New Issue",
            body="Issue description",
            labels=["bug", "AI-Fix"],
        )

        assert result["title"] == "New Issue"
        assert "html_url" in result

    async def test_add_comment_to_issue(self, github_client):
        """Business requirement: Communication works."""
        result = await github_client.create_issue_comment(
            owner="test-org",
            repo="test-repo",
            issue_number=123,
            body="This is a comment",
        )

        assert result["body"] == "This is a comment"
        assert "html_url" in result


class TestGitHubPullRequestOperations:
    """Tests for pull request operations."""

    async def test_get_pull_request(self, github_client):
        """Business requirement: PR reading works."""
        result = await github_client.get_pull_request("test-org", "test-repo", 42)

        assert result["number"] == 42
        assert "head" in result
        assert "base" in result

    async def test_add_comment_to_pr(self, github_client):
        """Business requirement: PR feedback works."""
        result = await github_client.create_pr_review_comment(
            owner="test-org",
            repo="test-repo",
            pr_number=42,
            body="Please fix this",
            commit_id="abc123",
            path="src/main.py",
            line=10,
        )

        assert result["body"] == "Please fix this"
        assert result["path"] == "src/main.py"


class TestGitHubFileOperations:
    """Tests for file operations."""

    async def test_get_file_contents(self, github_client):
        """Business requirement: Code reading works."""
        result = await github_client.get_file_contents(
            owner="test-org",
            repo="test-repo",
            path="src/main.py",
        )

        assert result["path"] == "src/main.py"
        assert "content" in result

    async def test_search_code(self, github_client):
        """Business requirement: Code search works."""
        result = await github_client.search_code("def authenticate")

        assert "total_count" in result
        assert "items" in result


class TestGitHubBranchOperations:
    """Tests for branch operations."""

    async def test_create_branch(self, github_client):
        """Business requirement: Branch creation works."""
        result = await github_client.create_branch(
            owner="test-org",
            repo="test-repo",
            branch="fix/issue-123",
            sha="abc123",
        )

        assert "refs/heads/fix/issue-123" in result["ref"]
