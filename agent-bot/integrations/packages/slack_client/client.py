"""Slack API client implementation."""

from typing import Any
import httpx
from .models import Message, Channel, User, File
from .exceptions import SlackAPIError, SlackAuthError, SlackNotFoundError


class SlackClient:
    """Async Slack API client."""

    BASE_URL = "https://slack.com/api"

    def __init__(self, bot_token: str, timeout: float = 30.0) -> None:
        self.bot_token = bot_token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "SlackClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {self.bot_token}"},
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make authenticated API request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        response = await self._client.request(method, endpoint, **kwargs)

        if response.status_code >= 400:
            raise SlackAPIError(
                f"HTTP {response.status_code}: {response.text}",
                error_code=str(response.status_code),
            )

        data = response.json()

        if not data.get("ok"):
            error = data.get("error", "unknown_error")
            if error == "not_authed" or error == "invalid_auth":
                raise SlackAuthError(error)
            elif error in ["channel_not_found", "user_not_found"]:
                raise SlackNotFoundError(error)
            else:
                raise SlackAPIError(f"Slack API error: {error}", error_code=error)

        return data

    async def send_message(
        self, channel: str, text: str, thread_ts: str | None = None
    ) -> Message:
        """Send a message to a channel."""
        payload = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        data = await self._request("POST", "/chat.postMessage", json=payload)
        return Message(
            ts=data["ts"], channel=data["channel"], text=text, thread_ts=thread_ts
        )

    async def get_channel_history(
        self, channel: str, limit: int = 100
    ) -> list[Message]:
        """Get channel message history."""
        data = await self._request(
            "GET", "/conversations.history", params={"channel": channel, "limit": limit}
        )
        return [Message(**msg) for msg in data.get("messages", [])]

    async def upload_file(
        self, channels: list[str], file_path: str, title: str | None = None
    ) -> File:
        """Upload a file to channels."""
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = await self._request(
                "POST",
                "/files.upload",
                data={"channels": ",".join(channels), "title": title},
                files=files,
            )
        return File(**data["file"])

    async def add_reaction(self, channel: str, timestamp: str, reaction: str) -> None:
        """Add reaction emoji to a message."""
        await self._request(
            "POST",
            "/reactions.add",
            json={"channel": channel, "timestamp": timestamp, "name": reaction},
        )
