"""GitHub API client implementation."""

from typing import Any
import httpx
from .models import Repository, PullRequest, Issue, Comment
from .exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)


class GitHubClient:
    """Async GitHub API client."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, timeout: float = 30.0) -> None:
        self.token = token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GitHubClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make authenticated API request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        response = await self._client.request(method, endpoint, **kwargs)

        if response.status_code == 401:
            raise GitHubAuthError()
        elif response.status_code == 404:
            raise GitHubNotFoundError(endpoint)
        elif response.status_code == 429:
            reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
            raise GitHubRateLimitError(reset_time)
        elif response.status_code >= 400:
            raise GitHubAPIError(
                f"API request failed: {response.text}", status_code=response.status_code
            )

        return response.json()

    async def get_repository(self, owner: str, repo: str) -> Repository:
        """Get repository details."""
        data = await self._request("GET", f"/repos/{owner}/{repo}")
        return Repository(**data)

    async def list_pull_requests(
        self, owner: str, repo: str, state: str = "open"
    ) -> list[PullRequest]:
        """List pull requests."""
        data = await self._request(
            "GET", f"/repos/{owner}/{repo}/pulls", params={"state": state}
        )
        return [PullRequest(**pr) for pr in data]

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> PullRequest:
        """Get pull request details."""
        data = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        return PullRequest(**data)

    async def create_pull_request(
        self, owner: str, repo: str, title: str, head: str, base: str, body: str | None = None
    ) -> PullRequest:
        """Create a pull request."""
        data = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            json={"title": title, "head": head, "base": base, "body": body},
        )
        return PullRequest(**data)

    async def create_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> Comment:
        """Create issue comment."""
        data = await self._request(
            "POST", f"/repos/{owner}/{repo}/issues/{issue_number}/comments", json={"body": body}
        )
        return Comment(**data)

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> Issue:
        """Get issue details."""
        data = await self._request("GET", f"/repos/{owner}/{repo}/issues/{issue_number}")
        return Issue(**data)
