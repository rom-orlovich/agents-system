from pydantic import BaseModel, ConfigDict
from typing import Literal


Platform = Literal["github", "jira", "slack"]


class OAuthCallbackRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    code: str
    state: str


class GitHubOAuthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    access_token: str
    token_type: str
    scope: str


class GitHubInstallation(BaseModel):
    model_config = ConfigDict(strict=True)

    id: int
    account: dict[str, str | int]


class SlackOAuthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    ok: bool
    access_token: str
    scope: str
    bot_user_id: str
    app_id: str
    team: dict[str, str]


class JiraOAuthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    access_token: str
    refresh_token: str
    expires_in: int
    scope: str


class OAuthState(BaseModel):
    model_config = ConfigDict(strict=True)

    nonce: str
    redirect_uri: str
    platform: Platform
