"""Sentry API client implementation."""

from typing import Any
import httpx
from .models import Issue, Event, Project
from .exceptions import SentryAPIError, SentryAuthError, SentryNotFoundError


class SentryClient:
    """Async Sentry API client."""

    BASE_URL = "https://sentry.io/api/0"

    def __init__(self, auth_token: str, timeout: float = 30.0) -> None:
        self.auth_token = auth_token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "SentryClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {self.auth_token}"},
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
            raise SentryAuthError()
        elif response.status_code == 404:
            raise SentryNotFoundError(endpoint)
        elif response.status_code >= 400:
            raise SentryAPIError(
                f"API request failed: {response.text}", status_code=response.status_code
            )

        return response.json()

    async def get_issue(self, issue_id: str) -> Issue:
        """Get issue by ID."""
        data = await self._request("GET", f"/issues/{issue_id}/")
        return Issue(**data)

    async def search_issues(
        self, organization: str, project: str, query: str | None = None
    ) -> list[Issue]:
        """Search issues in a project."""
        params = {"project": project}
        if query:
            params["query"] = query

        data = await self._request(
            "GET", f"/organizations/{organization}/issues/", params=params
        )
        return [Issue(**issue) for issue in data]

    async def update_issue(
        self, issue_id: str, status: str | None = None, assignedTo: str | None = None
    ) -> Issue:
        """Update issue status or assignee."""
        payload: dict[str, Any] = {}
        if status:
            payload["status"] = status
        if assignedTo:
            payload["assignedTo"] = assignedTo

        data = await self._request("PUT", f"/issues/{issue_id}/", json=payload)
        return Issue(**data)

    async def get_events(self, issue_id: str, limit: int = 10) -> list[Event]:
        """Get events for an issue."""
        data = await self._request(
            "GET", f"/issues/{issue_id}/events/", params={"limit": limit}
        )
        return [Event(**event) for event in data]

    async def create_comment(self, issue_id: str, text: str) -> dict[str, Any]:
        """Create a comment on an issue."""
        data = await self._request(
            "POST", f"/issues/{issue_id}/notes/", json={"text": text}
        )
        return data
