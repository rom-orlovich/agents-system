from typing import Any
import httpx
import structlog

logger = structlog.get_logger(__name__)


class GitHubClient:
    def __init__(self, token: str, base_url: str, timeout: int = 30):
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/repos/{owner}/{repo}")
        response.raise_for_status()
        return response.json()

    async def get_issue(
        self, owner: str, repo: str, issue_number: int
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/repos/{owner}/{repo}/issues/{issue_number}")
        response.raise_for_status()
        return response.json()

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        payload: dict[str, Any] = {"title": title}
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        response = await client.post(f"/repos/{owner}/{repo}/issues", json=payload)
        response.raise_for_status()
        return response.json()

    async def create_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()

    async def get_pull_request(
        self, owner: str, repo: str, pr_number: int
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        response.raise_for_status()
        return response.json()

    async def create_pr_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        commit_id: str,
        path: str,
        line: int,
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
            json={
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_file_contents(
        self, owner: str, repo: str, path: str, ref: str | None = None
    ) -> dict[str, Any]:
        client = await self._get_client()
        params = {"ref": ref} if ref else {}
        response = await client.get(
            f"/repos/{owner}/{repo}/contents/{path}", params=params
        )
        response.raise_for_status()
        return response.json()

    async def search_code(
        self, query: str, per_page: int = 30, page: int = 1
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(
            "/search/code", params={"q": query, "per_page": per_page, "page": page}
        )
        response.raise_for_status()
        return response.json()

    async def list_branches(
        self, owner: str, repo: str, per_page: int = 30, page: int = 1
    ) -> list[dict[str, Any]]:
        client = await self._get_client()
        response = await client.get(
            f"/repos/{owner}/{repo}/branches",
            params={"per_page": per_page, "page": page},
        )
        response.raise_for_status()
        return response.json()
