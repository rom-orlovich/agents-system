"""GitHub data models."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class User(BaseModel):
    """GitHub user."""

    model_config = ConfigDict(strict=True, frozen=True)

    login: str
    id: int
    avatar_url: HttpUrl
    url: HttpUrl


class Repository(BaseModel):
    """GitHub repository."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: int
    name: str
    full_name: str
    owner: User
    html_url: HttpUrl
    description: str | None = None
    private: bool
    default_branch: str = Field(default="main")


class Issue(BaseModel):
    """GitHub issue."""

    model_config = ConfigDict(strict=True)

    id: int
    number: int
    title: str
    body: str | None = None
    state: Literal["open", "closed"]
    user: User
    created_at: datetime
    updated_at: datetime
    html_url: HttpUrl


class PullRequest(BaseModel):
    """GitHub pull request."""

    model_config = ConfigDict(strict=True)

    id: int
    number: int
    title: str
    body: str | None = None
    state: Literal["open", "closed", "merged"]
    user: User
    head: str
    base: str
    created_at: datetime
    updated_at: datetime
    html_url: HttpUrl
    draft: bool = Field(default=False)


class Comment(BaseModel):
    """GitHub comment."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: int
    body: str
    user: User
    created_at: datetime
    updated_at: datetime
    html_url: HttpUrl
