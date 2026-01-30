"""Slack data models."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class User(BaseModel):
    """Slack user."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: str
    name: str
    real_name: str | None = None
    is_bot: bool = Field(default=False)


class Channel(BaseModel):
    """Slack channel."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: str
    name: str
    is_private: bool = Field(default=False)
    is_archived: bool = Field(default=False)


class Message(BaseModel):
    """Slack message."""

    model_config = ConfigDict(strict=True)

    ts: str
    channel: str
    text: str
    user: str | None = None
    thread_ts: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class File(BaseModel):
    """Slack file."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: str
    name: str
    mimetype: str
    size: int
    url_private: str
