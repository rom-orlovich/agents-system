"""Jira API client implementation."""

from typing import Any
from base64 import b64encode
import httpx
from .models import Issue, Project, Sprint, Transition
from .exceptions import JiraAPIError, JiraAuthError, JiraNotFoundError


class JiraClient:
    """Async Jira API client."""

    def __init__(self, url: str, email: str, api_token: str, timeout: float = 30.0) -> None:
        self.url = url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "JiraClient":
        """Async context manager entry."""
        auth_string = f"{self.email}:{self.api_token}"
        encoded_auth = b64encode(auth_string.encode()).decode()

        self._client = httpx.AsyncClient(
            base_url=f"{self.url}/rest/api/3",
            headers={
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        """Make authenticated API request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        response = await self._client.request(method, endpoint, **kwargs)

        if response.status_code == 401:
            raise JiraAuthError()
        elif response.status_code == 404:
            raise JiraNotFoundError(endpoint)
        elif response.status_code >= 400:
            raise JiraAPIError(
                f"API request failed: {response.text}", status_code=response.status_code
            )

        return response.json()

    async def get_issue(self, issue_key: str) -> Issue:
        """Get issue by key."""
        data = await self._request("GET", f"/issue/{issue_key}")
        return Issue(**data)

    async def search_issues(self, jql: str, max_results: int = 50) -> list[Issue]:
        """Search issues using JQL."""
        data = await self._request(
            "GET", "/search", params={"jql": jql, "maxResults": max_results}
        )
        return [Issue(**issue) for issue in data["issues"]]

    async def create_issue(
        self, project_key: str, summary: str, issue_type: str, description: str | None = None
    ) -> Issue:
        """Create a new issue."""
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
                "description": description,
            }
        }
        data = await self._request("POST", "/issue", json=payload)
        return await self.get_issue(data["key"])

    async def update_issue(self, issue_key: str, fields: dict[str, Any]) -> None:
        """Update issue fields."""
        await self._request("PUT", f"/issue/{issue_key}", json={"fields": fields})

    async def get_transitions(self, issue_key: str) -> list[Transition]:
        """Get available transitions for issue."""
        data = await self._request("GET", f"/issue/{issue_key}/transitions")
        return [Transition(**t) for t in data["transitions"]]

    async def transition_issue(self, issue_key: str, transition_id: str) -> None:
        """Transition issue to new status."""
        await self._request(
            "POST", f"/issue/{issue_key}/transitions", json={"transition": {"id": transition_id}}
        )
