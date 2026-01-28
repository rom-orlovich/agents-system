"""Slack API client for notifications and workflow automation."""

import os
import httpx
import structlog
from typing import Optional, Dict, Any, List
from domain.retry import with_retry

logger = structlog.get_logger()


class SlackClient:
    """Client for interacting with Slack API."""

    def __init__(self, bot_token: Optional[str] = None):
        """Initialize Slack client with bot token."""
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.base_url = "https://slack.com/api"

        self.headers = {
            "Content-Type": "application/json"
        }

        if self.bot_token:
            self.headers["Authorization"] = f"Bearer {self.bot_token}"
        else:
            logger.warning("slack_client_no_token", message="SLACK_BOT_TOKEN not configured")

    def _check_config(self) -> None:
        """Check if client is properly configured."""
        if not self.bot_token:
            raise ValueError("Slack client not properly configured. Check SLACK_BOT_TOKEN")

    @with_retry(max_attempts=3, wait_min=1, wait_max=5, retry_on=(ConnectionError, TimeoutError, httpx.ConnectError, httpx.TimeoutException))
    async def post_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Post a message to a Slack channel.

        Args:
            channel: Channel ID or name (e.g., "#general" or "C1234567890")
            text: Message text (fallback for notifications)
            blocks: Optional Block Kit blocks for rich formatting
            thread_ts: Optional thread timestamp to reply in thread

        Returns:
            API response dict
        """
        self._check_config()

        url = f"{self.base_url}/chat.postMessage"

        payload: Dict[str, Any] = {
            "channel": channel,
            "text": text
        }

        if blocks:
            payload["blocks"] = blocks

        if thread_ts:
            payload["thread_ts"] = thread_ts

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()

                if not data.get("ok"):
                    error = data.get("error", "unknown")
                    logger.error("slack_post_message_failed", channel=channel, error=error)
                    raise Exception(f"Slack API error: {error}")

                logger.info(
                    "slack_message_posted",
                    channel=channel,
                    ts=data.get("ts")
                )

                return data

        except httpx.HTTPStatusError as e:
            logger.error(
                "slack_api_http_error",
                channel=channel,
                status_code=e.response.status_code,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "slack_api_error",
                channel=channel,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def post_ephemeral(
        self,
        channel: str,
        user: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Post an ephemeral message (visible only to specific user).

        Args:
            channel: Channel ID
            user: User ID who should see the message
            text: Message text
            blocks: Optional Block Kit blocks

        Returns:
            API response dict
        """
        self._check_config()

        url = f"{self.base_url}/chat.postEphemeral"

        payload: Dict[str, Any] = {
            "channel": channel,
            "user": user,
            "text": text
        }

        if blocks:
            payload["blocks"] = blocks

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()

                if not data.get("ok"):
                    error = data.get("error", "unknown")
                    logger.error("slack_ephemeral_failed", channel=channel, error=error)
                    raise Exception(f"Slack API error: {error}")

                logger.info("slack_ephemeral_posted", channel=channel, user=user)
                return data

        except Exception as e:
            logger.error("slack_ephemeral_error", channel=channel, user=user, error=str(e))
            raise

    async def add_reaction(
        self,
        channel: str,
        timestamp: str,
        reaction: str
    ) -> Dict[str, Any]:
        """
        Add a reaction emoji to a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            reaction: Emoji name (without colons, e.g., "thumbsup")

        Returns:
            API response dict
        """
        self._check_config()

        url = f"{self.base_url}/reactions.add"

        payload = {
            "channel": channel,
            "timestamp": timestamp,
            "name": reaction
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()

                if not data.get("ok"):
                    error = data.get("error", "unknown")
                    if error != "already_reacted":  # Don't log if already reacted
                        logger.error("slack_reaction_failed", channel=channel, error=error)
                    raise Exception(f"Slack API error: {error}")

                logger.info("slack_reaction_added", channel=channel, reaction=reaction)
                return data

        except Exception as e:
            logger.error("slack_reaction_error", channel=channel, reaction=reaction, error=str(e))
            raise

    async def update_message(
        self,
        channel: str,
        timestamp: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            text: New message text
            blocks: Optional new Block Kit blocks

        Returns:
            API response dict
        """
        self._check_config()

        url = f"{self.base_url}/chat.update"

        payload: Dict[str, Any] = {
            "channel": channel,
            "ts": timestamp,
            "text": text
        }

        if blocks:
            payload["blocks"] = blocks

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()

                if not data.get("ok"):
                    error = data.get("error", "unknown")
                    logger.error("slack_update_failed", channel=channel, error=error)
                    raise Exception(f"Slack API error: {error}")

                logger.info("slack_message_updated", channel=channel, ts=timestamp)
                return data

        except Exception as e:
            logger.error("slack_update_error", channel=channel, ts=timestamp, error=str(e))
            raise

    async def send_workflow_notification(
        self,
        channel: str,
        workflow_name: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a formatted workflow notification with status.

        Args:
            channel: Channel ID or name
            workflow_name: Name of the workflow
            status: Status (started, in_progress, completed, failed)
            details: Optional details dict
            thread_ts: Optional thread to reply in

        Returns:
            API response dict
        """
        status_emojis = {
            "started": "🚀",
            "in_progress": "⚙️",
            "completed": "✅",
            "failed": "❌",
            "warning": "⚠️"
        }

        emoji = status_emojis.get(status, "📋")
        text = f"{emoji} *{workflow_name}*: {status.replace('_', ' ').title()}"

        blocks: List[Dict[str, Any]] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            }
        ]

        if details:
            fields = []
            for key, value in details.items():
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:*\n{value}"
                })

            if fields:
                blocks.append({
                    "type": "section",
                    "fields": fields
                })

        return await self.post_message(
            channel=channel,
            text=text,
            blocks=blocks,
            thread_ts=thread_ts
        )


# Global client instance
slack_client = SlackClient()
