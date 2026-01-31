from typing import Any
import httpx
import structlog

logger = structlog.get_logger(__name__)


class SlackClient:
    def __init__(self, bot_token: str, base_url: str, timeout: int = 30):
        self._bot_token = bot_token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._bot_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _check_response(self, data: dict[str, Any]) -> dict[str, Any]:
        if not data.get("ok"):
            error = data.get("error", "Unknown error")
            raise SlackAPIError(error)
        return data

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
        response = await client.post("/chat.postMessage", json=payload)
        response.raise_for_status()
        return self._check_response(response.json())

    async def get_channel_history(
        self,
        channel: str,
        limit: int = 100,
        oldest: str | None = None,
        latest: str | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        params: dict[str, Any] = {"channel": channel, "limit": limit}
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest
        response = await client.get("/conversations.history", params=params)
        response.raise_for_status()
        return self._check_response(response.json())

    async def get_thread_replies(
        self, channel: str, thread_ts: str, limit: int = 100
    ) -> dict[str, Any]:
        client = await self._get_client()
        params = {"channel": channel, "ts": thread_ts, "limit": limit}
        response = await client.get("/conversations.replies", params=params)
        response.raise_for_status()
        return self._check_response(response.json())

    async def add_reaction(
        self, channel: str, timestamp: str, emoji: str
    ) -> dict[str, Any]:
        client = await self._get_client()
        payload = {"channel": channel, "timestamp": timestamp, "name": emoji}
        response = await client.post("/reactions.add", json=payload)
        response.raise_for_status()
        return self._check_response(response.json())

    async def get_channel_info(self, channel: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get("/conversations.info", params={"channel": channel})
        response.raise_for_status()
        return self._check_response(response.json())

    async def list_channels(
        self, limit: int = 100, cursor: str | None = None
    ) -> dict[str, Any]:
        client = await self._get_client()
        params: dict[str, Any] = {
            "limit": limit,
            "types": "public_channel,private_channel",
        }
        if cursor:
            params["cursor"] = cursor
        response = await client.get("/conversations.list", params=params)
        response.raise_for_status()
        return self._check_response(response.json())

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get("/users.info", params={"user": user_id})
        response.raise_for_status()
        return self._check_response(response.json())

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
        response = await client.post("/chat.update", json=payload)
        response.raise_for_status()
        return self._check_response(response.json())


class SlackAPIError(Exception):
    pass
