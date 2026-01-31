from typing import Any
import httpx

from config import get_settings


class JiraAPI:
    def __init__(self):
        settings = get_settings()
        self._base_url = settings.jira_api_url.rstrip("/")
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

    async def get_issue(self, issue_key: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/api/v1/issues/{issue_key}")
        response.raise_for_status()
        return response.json()

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            "/api/v1/issues",
            json={
                "project_key": project_key,
                "summary": summary,
                "description": description,
                "issue_type": issue_type,
            },
        )
        response.raise_for_status()
        return response.json()

    async def update_issue(
        self, issue_key: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.put(
            f"/api/v1/issues/{issue_key}",
            json={"fields": fields},
        )
        response.raise_for_status()
        return response.json()

    async def add_comment(self, issue_key: str, body: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            f"/api/v1/issues/{issue_key}/comments",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()

    async def search_issues(
        self, jql: str, max_results: int = 50, start_at: int = 0
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            "/api/v1/search",
            json={"jql": jql, "max_results": max_results, "start_at": start_at},
        )
        response.raise_for_status()
        return response.json()

    async def get_transitions(self, issue_key: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/api/v1/issues/{issue_key}/transitions")
        response.raise_for_status()
        return response.json()

    async def transition_issue(
        self, issue_key: str, transition_id: str
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            f"/api/v1/issues/{issue_key}/transitions",
            json={"transition_id": transition_id},
        )
        response.raise_for_status()
        return response.json()
