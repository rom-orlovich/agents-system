import httpx
import os
import structlog
from typing import Dict, Any

logger = structlog.get_logger()


class SlackClient:
    def __init__(self, bot_token: str | None = None, timeout: int = 30):
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN", "")
        self.base_url = "https://slack.com/api"
        self.timeout = timeout

        if not self.bot_token:
            raise ValueError("Slack bot token not configured")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }

    async def post_message(
        self, channel: str, text: str, thread_ts: str | None = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat.postMessage"
        payload: Dict[str, Any] = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                if not data.get("ok"):
                    raise Exception(data.get("error", "Unknown error"))
                return data
            except httpx.HTTPError as e:
                logger.error("slack_post_message_failed", channel=channel, error=str(e))
                raise

    async def update_message(
        self, channel: str, ts: str, text: str
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat.update"
        payload = {"channel": channel, "ts": ts, "text": text}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                if not data.get("ok"):
                    raise Exception(data.get("error", "Unknown error"))
                return data
            except httpx.HTTPError as e:
                logger.error(
                    "slack_update_message_failed",
                    channel=channel,
                    ts=ts,
                    error=str(e),
                )
                raise
