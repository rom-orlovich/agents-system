from typing import Any
import httpx

from config import get_settings


class KnowledgeGraphClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.knowledge_graph_url.rstrip("/")
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

    async def search_nodes(
        self,
        query: str,
        node_types: list[str] | None = None,
        language: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            "/api/v1/query/search",
            json={
                "query": query,
                "node_types": node_types,
                "language": language,
                "limit": limit,
            },
        )
        response.raise_for_status()
        return response.json()

    async def find_neighbors(
        self,
        node_id: str,
        edge_types: list[str] | None = None,
        direction: str = "both",
        depth: int = 1,
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            "/api/v1/query/neighbors",
            json={
                "node_id": node_id,
                "edge_types": edge_types,
                "direction": direction,
                "depth": depth,
            },
        )
        response.raise_for_status()
        return response.json()

    async def find_path(
        self,
        source_id: str,
        target_id: str,
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            "/api/v1/query/path",
            json={
                "source_id": source_id,
                "target_id": target_id,
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_node(self, node_id: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/api/v1/nodes/{node_id}")
        response.raise_for_status()
        return response.json()

    async def list_nodes(
        self,
        node_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        client = await self._get_client()
        params: dict[str, Any] = {"limit": limit}
        if node_type:
            params["node_type"] = node_type
        response = await client.get("/api/v1/nodes", params=params)
        response.raise_for_status()
        return response.json()

    async def get_stats(self) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get("/api/v1/stats")
        response.raise_for_status()
        return response.json()

    async def find_symbol_references(
        self,
        symbol_name: str,
        repository: str | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            "/api/v1/query/search",
            json={
                "query": symbol_name,
                "node_types": ["function", "class", "method", "variable"],
                "limit": 50,
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_file_structure(
        self,
        repository: str,
        path: str | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            "/api/v1/query/search",
            json={
                "query": path or repository,
                "node_types": ["file", "directory", "module"],
                "limit": 100,
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_dependencies(
        self,
        node_id: str,
        direction: str = "outgoing",
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            "/api/v1/query/neighbors",
            json={
                "node_id": node_id,
                "edge_types": ["imports", "calls", "inherits", "uses"],
                "direction": direction,
                "depth": 1,
            },
        )
        response.raise_for_status()
        return response.json()
