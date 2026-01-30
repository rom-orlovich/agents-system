from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class Platform(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    JIRA = "jira"
    SLACK = "slack"


class Installation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    platform: Platform
    organization_id: str
    organization_name: str
    access_token: str
    refresh_token: str | None
    scopes: list[str]
    webhook_secret: str
    installed_by: str
    created_at: datetime
    updated_at: datetime


class InstallationCreate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    platform: Platform
    organization_id: str
    organization_name: str
    access_token: str
    refresh_token: str | None
    scopes: list[str]
    webhook_secret: str
    installed_by: str


class InstallationUpdate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    access_token: str | None = None
    refresh_token: str | None = None
    scopes: list[str] | None = None
    webhook_secret: str | None = None
