"""Slack API routes."""

from typing import Any
from fastapi import APIRouter, HTTPException, status
import structlog
import sys

sys.path.insert(0, "../../packages")
from slack_client import SlackClient, SlackAPIError

router = APIRouter()
logger = structlog.get_logger()


@router.post("/messages")
async def send_message(
    channel: str, text: str, bot_token: str, thread_ts: str | None = None
) -> dict[str, Any]:
    """Send a message to a channel."""
    try:
        async with SlackClient(bot_token=bot_token) as client:
            message = await client.send_message(channel, text, thread_ts)
            return message.model_dump()
    except SlackAPIError as e:
        logger.error("slack_api_error", error=str(e), channel=channel)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )


@router.get("/channels/{channel}/history")
async def get_channel_history(
    channel: str, bot_token: str, limit: int = 100
) -> list[dict[str, Any]]:
    """Get channel message history."""
    try:
        async with SlackClient(bot_token=bot_token) as client:
            messages = await client.get_channel_history(channel, limit)
            return [msg.model_dump() for msg in messages]
    except SlackAPIError as e:
        logger.error("slack_api_error", error=str(e), channel=channel)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )


@router.post("/reactions")
async def add_reaction(
    channel: str, timestamp: str, reaction: str, bot_token: str
) -> dict[str, str]:
    """Add reaction emoji to a message."""
    try:
        async with SlackClient(bot_token=bot_token) as client:
            await client.add_reaction(channel, timestamp, reaction)
            return {"status": "success", "channel": channel, "reaction": reaction}
    except SlackAPIError as e:
        logger.error("slack_api_error", error=str(e), channel=channel)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )
