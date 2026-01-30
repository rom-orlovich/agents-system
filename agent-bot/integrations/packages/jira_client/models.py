"""Jira data models."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class User(BaseModel):
    """Jira user."""

    model_config = ConfigDict(strict=True, frozen=True)

    account_id: str
    display_name: str
    email_address: str | None = None


class Project(BaseModel):
    """Jira project."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: str
    key: str
    name: str
    project_type_key: str


class IssueFields(BaseModel):
    """Jira issue fields."""

    model_config = ConfigDict(strict=True)

    summary: str
    description: str | None = None
    status: dict[str, Any]
    priority: dict[str, Any] | None = None
    assignee: User | None = None
    reporter: User | None = None
    created: datetime
    updated: datetime


class Issue(BaseModel):
    """Jira issue."""

    model_config = ConfigDict(strict=True)

    id: str
    key: str
    self_link: HttpUrl = Field(alias="self")
    fields: IssueFields


class Sprint(BaseModel):
    """Jira sprint."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: int
    name: str
    state: str
    start_date: datetime | None = None
    end_date: datetime | None = None


class Transition(BaseModel):
    """Jira transition."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: str
    name: str
