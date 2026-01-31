from typing import Any, Literal
import httpx

from config import get_settings

IssueStatus = Literal["resolved", "unresolved", "ignored"]


class SentryAPI:
    def __init__(self):
        settings = get_settings()
        self._base_url = settings.sentry_api_url.rstrip("/")
        self._timeout = settings.request_timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def list_projects(self) -> list[dict[str, Any]]:
        client = await self._get_client()
        response = await client.get("/api/v1/projects")
        response.raise_for_status()
        return response.json()

    async def get_project_issues(
        self,
        project_slug: str,
        query: str | None = None,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        client = await self._get_client()
        params: dict[str, Any] = {}
        if query:
            params["query"] = query
        if cursor:
            params["cursor"] = cursor
        response = await client.get(
            f"/api/v1/projects/{project_slug}/issues", params=params
        )
        response.raise_for_status()
        return response.json()

    async def get_issue(self, issue_id: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/api/v1/issues/{issue_id}")
        response.raise_for_status()
        return response.json()

    async def get_issue_events(
        self, issue_id: str, cursor: str | None = None
    ) -> list[dict[str, Any]]:
        client = await self._get_client()
        params = {"cursor": cursor} if cursor else {}
        response = await client.get(f"/api/v1/issues/{issue_id}/events", params=params)
        response.raise_for_status()
        return response.json()

    async def get_latest_event(self, issue_id: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/api/v1/issues/{issue_id}/events/latest")
        response.raise_for_status()
        return response.json()

    async def update_issue_status(
        self, issue_id: str, status: IssueStatus
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.put(
            f"/api/v1/issues/{issue_id}/status",
            json={"status": status},
        )
        response.raise_for_status()
        return response.json()

    async def add_comment(self, issue_id: str, text: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            f"/api/v1/issues/{issue_id}/comments",
            json={"text": text},
        )
        response.raise_for_status()
        return response.json()

    async def get_issue_tags(self, issue_id: str) -> list[dict[str, Any]]:
        client = await self._get_client()
        response = await client.get(f"/api/v1/issues/{issue_id}/tags")
        response.raise_for_status()
        return response.json()
