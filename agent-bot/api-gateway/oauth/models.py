import base64
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class OAuthState(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    platform: Literal["github", "slack", "jira"]
    redirect_uri: str
    nonce: str
    metadata: dict[str, str] = Field(default_factory=dict)

    def to_encoded(self) -> str:
        json_str = self.model_dump_json()
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    @classmethod
    def from_encoded(cls, encoded: str) -> "OAuthState":
        json_str = base64.urlsafe_b64decode(encoded.encode()).decode()
        return cls.model_validate_json(json_str)


class OAuthCallbackParams(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    code: str
    state: str
    error: str | None = None
    error_description: str | None = None


class OAuthError(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    error: str
    error_description: str


class GitHubTokenResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    access_token: str
    token_type: str
    scope: str
    refresh_token: str | None = None
    expires_in: int | None = None
    refresh_token_expires_in: int | None = None

    @computed_field
    @property
    def scopes(self) -> list[str]:
        return [s.strip() for s in self.scope.split(",") if s.strip()]


class GitHubInstallationInfo(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    installation_id: int
    account_id: int
    account_login: str
    account_type: Literal["User", "Organization"]
    permissions: dict[str, str] = Field(default_factory=dict)
