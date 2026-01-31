from typing import Any, Literal
import httpx
import structlog

logger = structlog.get_logger(__name__)

IssueStatus = Literal["resolved", "unresolved", "ignored"]


class SentryClient:
    def __init__(
        self, auth_token: str, org_slug: str, base_url: str, timeout: int = 30
    ):
        self._auth_token = auth_token
        self._org_slug = org_slug
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._auth_token}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def list_projects(self) -> list[dict[str, Any]]:
        client = await self._get_client()
        response = await client.get(f"/organizations/{self._org_slug}/projects/")
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
            f"/projects/{self._org_slug}/{project_slug}/issues/",
            params=params,
        )
        response.raise_for_status()
        return response.json()

    async def get_issue(self, issue_id: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/issues/{issue_id}/")
        response.raise_for_status()
        return response.json()

    async def get_issue_events(
        self, issue_id: str, cursor: str | None = None
    ) -> list[dict[str, Any]]:
        client = await self._get_client()
        params = {"cursor": cursor} if cursor else {}
        response = await client.get(f"/issues/{issue_id}/events/", params=params)
        response.raise_for_status()
        return response.json()

    async def get_latest_event(self, issue_id: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/issues/{issue_id}/events/latest/")
        response.raise_for_status()
        return response.json()

    async def update_issue_status(
        self, issue_id: str, status: IssueStatus
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.put(
            f"/issues/{issue_id}/",
            json={"status": status},
        )
        response.raise_for_status()
        return response.json()

    async def add_comment(self, issue_id: str, text: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            f"/issues/{issue_id}/comments/",
            json={"text": text},
        )
        response.raise_for_status()
        return response.json()

    async def get_issue_hashes(self, issue_id: str) -> list[dict[str, Any]]:
        client = await self._get_client()
        response = await client.get(f"/issues/{issue_id}/hashes/")
        response.raise_for_status()
        return response.json()

    async def get_issue_tags(self, issue_id: str) -> list[dict[str, Any]]:
        client = await self._get_client()
        response = await client.get(f"/issues/{issue_id}/tags/")
        response.raise_for_status()
        return response.json()

    async def assign_issue(
        self, issue_id: str, assignee_id: str | None
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.put(
            f"/issues/{issue_id}/",
            json={"assignedTo": assignee_id},
        )
        response.raise_for_status()
        return response.json()

    async def get_organization_members(self) -> list[dict[str, Any]]:
        client = await self._get_client()
        response = await client.get(f"/organizations/{self._org_slug}/members/")
        response.raise_for_status()
        return response.json()
