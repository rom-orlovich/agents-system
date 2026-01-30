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

    team_id: str
    team_name: str
    access_token: str
    bot_user_id: str
    scopes: list[str]
    expires_at: int | None


class JiraOAuthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    cloud_id: str
    site_url: str
    access_token: str
    refresh_token: str
    scopes: list[str]
    expires_at: int | None
