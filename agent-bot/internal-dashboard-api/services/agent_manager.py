from typing import Any
import httpx
import structlog

from config import get_settings

logger = structlog.get_logger(__name__)


class AgentManager:
    def __init__(self):
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.agent_engine_url,
                timeout=30,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_agent_status(self) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get("/status")
        response.raise_for_status()
        return response.json()

    async def get_agent_health(self) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get("/health")
        response.raise_for_status()
        return response.json()

    async def list_agents(self) -> list[dict[str, Any]]:
        status = await self.get_agent_status()
        return [
            {
                "id": "agent-engine",
                "type": "main",
                "status": "running" if status.get("worker_running") else "stopped",
                "provider": status.get("cli_provider"),
                "max_concurrent": status.get("max_concurrent_tasks"),
            }
        ]

    async def get_agent_metrics(self) -> dict[str, Any]:
        status = await self.get_agent_status()
        return {
            "total_agents": 1,
            "active_agents": 1 if status.get("worker_running") else 0,
            "cli_provider": status.get("cli_provider"),
        }
