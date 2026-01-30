"""Sentry data models."""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class Project(BaseModel):
    """Sentry project."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: str
    slug: str
    name: str
    platform: str | None = None


class Issue(BaseModel):
    """Sentry issue."""

    model_config = ConfigDict(strict=True)

    id: str
    title: str
    culprit: str | None = None
    status: Literal["resolved", "unresolved", "ignored"]
    level: str
    count: int = Field(default=0)
    first_seen: datetime
    last_seen: datetime
    permalink: HttpUrl


class Event(BaseModel):
    """Sentry event."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: str
    event_id: str
    message: str
    timestamp: datetime
    platform: str
    tags: dict[str, Any] = Field(default_factory=dict)
