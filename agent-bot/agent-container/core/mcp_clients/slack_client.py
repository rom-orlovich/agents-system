import structlog
from typing import Any

logger = structlog.get_logger()


class SlackMCPClient:
    def __init__(self, mcp_client: Any) -> None:
        self._client = mcp_client

    async def post_message(
        self,
        channel: str,
        text: str,
        thread_ts: str | None = None,
    ) -> bool:
        try:
            arguments: dict[str, Any] = {
                "channel": channel,
                "text": text,
            }

            if thread_ts:
                arguments["thread_ts"] = thread_ts

            result = await self._client.call_tool(
                name="slack_post_message",
                arguments=arguments,
            )

            logger.info(
                "slack_message_posted",
                channel=channel,
                thread_ts=thread_ts,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "slack_post_failed",
                channel=channel,
                error=str(e),
            )
            return False

    async def add_reaction(
        self,
        channel: str,
        timestamp: str,
        emoji: str,
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="slack_add_reaction",
                arguments={
                    "channel": channel,
                    "timestamp": timestamp,
                    "name": emoji,
                },
            )

            logger.info(
                "slack_reaction_added",
                channel=channel,
                timestamp=timestamp,
                emoji=emoji,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "slack_reaction_failed",
                channel=channel,
                timestamp=timestamp,
                error=str(e),
            )
            return False

    async def update_message(
        self,
        channel: str,
        timestamp: str,
        text: str,
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="slack_update_message",
                arguments={
                    "channel": channel,
                    "timestamp": timestamp,
                    "text": text,
                },
            )

            logger.info(
                "slack_message_updated",
                channel=channel,
                timestamp=timestamp,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "slack_update_failed",
                channel=channel,
                timestamp=timestamp,
                error=str(e),
            )
            return False

    async def delete_message(
        self,
        channel: str,
        timestamp: str,
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="slack_delete_message",
                arguments={
                    "channel": channel,
                    "timestamp": timestamp,
                },
            )

            logger.info(
                "slack_message_deleted",
                channel=channel,
                timestamp=timestamp,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "slack_delete_failed",
                channel=channel,
                timestamp=timestamp,
                error=str(e),
            )
            return False
