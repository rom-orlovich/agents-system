from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class Platform(str, Enum):
    GITHUB = "github"
    SLACK = "slack"
    JIRA = "jira"
    SENTRY = "sentry"


class Installation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    platform: Platform
    organization_id: str
    organization_name: str
    access_token: str
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    scopes: list[str]
    webhook_secret: str
    installed_at: datetime
    installed_by: str
    metadata: dict[str, str] = Field(default_factory=dict)
    is_active: bool = True


class InstallationCreate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    platform: Platform
    organization_id: str
    organization_name: str
    access_token: str
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    scopes: list[str]
    webhook_secret: str
    installed_by: str
    metadata: dict[str, str] = Field(default_factory=dict)


class InstallationUpdate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    scopes: list[str] | None = None
    is_active: bool | None = None
    metadata: dict[str, str] | None = None


class TokenInfo(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    access_token: str
    expires_at: datetime | None
    scopes: list[str]

    @computed_field
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class InstallationFilter(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    platform: Platform | None = None
    organization_id: str | None = None
    is_active: bool | None = None
