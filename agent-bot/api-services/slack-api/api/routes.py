from typing import Annotated, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from client import SlackClient
from config import get_settings, Settings

router = APIRouter(prefix="/api/v1", tags=["slack"])


def get_slack_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SlackClient:
    return SlackClient(
        bot_token=settings.slack_bot_token,
        base_url=settings.slack_api_base_url,
        timeout=settings.request_timeout,
    )


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    channel: str
    text: str
    thread_ts: str | None = None
    blocks: list[dict[str, Any]] | None = None


class AddReactionRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    channel: str
    timestamp: str
    emoji: str


class UpdateMessageRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    channel: str
    ts: str
    text: str
    blocks: list[dict[str, Any]] | None = None


@router.post("/messages")
async def send_message(
    request: SendMessageRequest,
    client: Annotated[SlackClient, Depends(get_slack_client)],
):
    return await client.send_message(
        request.channel, request.text, request.thread_ts, request.blocks
    )


@router.get("/channels/{channel}/history")
async def get_channel_history(
    channel: str,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    oldest: Annotated[str | None, Query()] = None,
    latest: Annotated[str | None, Query()] = None,
    client: Annotated[SlackClient, Depends(get_slack_client)] = None,
):
    return await client.get_channel_history(channel, limit, oldest, latest)


@router.get("/channels/{channel}/threads/{thread_ts}")
async def get_thread_replies(
    channel: str,
    thread_ts: str,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    client: Annotated[SlackClient, Depends(get_slack_client)] = None,
):
    return await client.get_thread_replies(channel, thread_ts, limit)


@router.post("/reactions")
async def add_reaction(
    request: AddReactionRequest,
    client: Annotated[SlackClient, Depends(get_slack_client)],
):
    return await client.add_reaction(request.channel, request.timestamp, request.emoji)


@router.get("/channels/{channel}")
async def get_channel_info(
    channel: str,
    client: Annotated[SlackClient, Depends(get_slack_client)],
):
    return await client.get_channel_info(channel)


@router.get("/channels")
async def list_channels(
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    cursor: Annotated[str | None, Query()] = None,
    client: Annotated[SlackClient, Depends(get_slack_client)] = None,
):
    return await client.list_channels(limit, cursor)


@router.get("/users/{user_id}")
async def get_user_info(
    user_id: str,
    client: Annotated[SlackClient, Depends(get_slack_client)],
):
    return await client.get_user_info(user_id)


@router.put("/messages")
async def update_message(
    request: UpdateMessageRequest,
    client: Annotated[SlackClient, Depends(get_slack_client)],
):
    return await client.update_message(
        request.channel, request.ts, request.text, request.blocks
    )
