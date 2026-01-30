from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Literal

Platform = Literal["github", "slack", "jira", "sentry"]


class Installation(BaseModel):
    model_config = ConfigDict(strict=True)

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
    metadata: dict[str, str]
    is_active: bool = True
