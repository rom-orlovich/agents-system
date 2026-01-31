from typing import Any
import httpx

from config import get_settings


class SlackAPI:
    def __init__(self):
        settings = get_settings()
        self._base_url = settings.slack_api_url.rstrip("/")
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

    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: str | None = None,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        if blocks:
            payload["blocks"] = blocks
        response = await client.post("/api/v1/messages", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_channel_history(
        self,
        channel: str,
        limit: int = 100,
        oldest: str | None = None,
        latest: str | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        params: dict[str, Any] = {"limit": limit}
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest
        response = await client.get(
            f"/api/v1/channels/{channel}/history", params=params
        )
        response.raise_for_status()
        return response.json()

    async def get_thread_replies(
        self, channel: str, thread_ts: str, limit: int = 100
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(
            f"/api/v1/channels/{channel}/threads/{thread_ts}",
            params={"limit": limit},
        )
        response.raise_for_status()
        return response.json()

    async def add_reaction(
        self, channel: str, timestamp: str, emoji: str
    ) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.post(
            "/api/v1/reactions",
            json={"channel": channel, "timestamp": timestamp, "emoji": emoji},
        )
        response.raise_for_status()
        return response.json()

    async def get_channel_info(self, channel: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/api/v1/channels/{channel}")
        response.raise_for_status()
        return response.json()

    async def list_channels(
        self, limit: int = 100, cursor: str | None = None
    ) -> dict[str, Any]:
        client = await self._get_client()
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        response = await client.get("/api/v1/channels", params=params)
        response.raise_for_status()
        return response.json()

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"/api/v1/users/{user_id}")
        response.raise_for_status()
        return response.json()

    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        payload: dict[str, Any] = {"channel": channel, "ts": ts, "text": text}
        if blocks:
            payload["blocks"] = blocks
        response = await client.put("/api/v1/messages", json=payload)
        response.raise_for_status()
        return response.json()
