from pydantic import BaseModel, ConfigDict


class GitHubOAuthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    access_token: str
    token_type: str
    scope: str


class GitHubInstallation(BaseModel):
    model_config = ConfigDict(strict=True)

    installation_id: int
    account_login: str
    account_id: int
    repository_selection: str
    permissions: dict[str, str]


class SlackOAuthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    access_token: str
    token_type: str
    scope: str
    bot_user_id: str
    app_id: str
    team: dict[str, str]
    authed_user: dict[str, str]


class JiraOAuthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    access_token: str
    refresh_token: str
    expires_in: int
    scope: str
    cloud_id: str
