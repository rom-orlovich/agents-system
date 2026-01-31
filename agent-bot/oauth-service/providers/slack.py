import httpx
import structlog

from config.settings import Settings

from .base import InstallationInfo, OAuthProvider, OAuthTokens

logger = structlog.get_logger(__name__)

DEFAULT_SCOPES = [
    "chat:write",
    "channels:read",
    "app_mentions:read",
    "users:read",
    "reactions:write",
]


class SlackOAuthProvider(OAuthProvider):
    def __init__(self, settings: Settings):
        self.client_id = settings.slack_client_id
        self.client_secret = settings.slack_client_secret
        self.redirect_uri = f"{settings.base_url}/oauth/callback/slack"
        self.scopes = DEFAULT_SCOPES

    def get_authorization_url(self, state: str) -> str:
        scope_str = ",".join(self.scopes)
        return (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={self.client_id}"
            f"&scope={scope_str}"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
        )

    async def exchange_code(self, code: str, state: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise ValueError(f"Slack OAuth error: {data.get('error')}")

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            scopes=data.get("scope", "").split(","),
        )

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise ValueError(f"Slack refresh error: {data.get('error')}")

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
        )

    async def get_installation_info(self, tokens: OAuthTokens) -> InstallationInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/team.info",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise ValueError(f"Slack team.info error: {data.get('error')}")

        team = data["team"]
        return InstallationInfo(
            external_org_id=team["id"],
            external_org_name=team["name"],
            external_install_id=None,
            installed_by=None,
            permissions={scope: "granted" for scope in tokens.scopes or []},
            metadata={
                "domain": team.get("domain"),
                "icon": team.get("icon", {}).get("image_132"),
            },
        )

    async def revoke_tokens(self, tokens: OAuthTokens) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/auth.revoke",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            data = response.json()
        return data.get("ok", False)
