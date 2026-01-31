from datetime import datetime, timezone

import httpx
import jwt
import structlog

from config.settings import Settings

from .base import InstallationInfo, OAuthProvider, OAuthTokens

logger = structlog.get_logger(__name__)


class GitHubOAuthProvider(OAuthProvider):
    def __init__(self, settings: Settings):
        self.app_id = settings.github_app_id
        self.app_name = settings.github_app_name
        self.client_id = settings.github_client_id
        self.client_secret = settings.github_client_secret
        self.private_key = settings.github_private_key
        self.redirect_uri = f"{settings.base_url}/oauth/callback/github"

    def get_authorization_url(self, state: str) -> str:
        return (
            f"https://github.com/apps/{self.app_name}/installations/new?state={state}"
        )

    def _generate_jwt(self) -> str:
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": self.app_id,
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def exchange_code(self, code: str, state: str) -> OAuthTokens:
        return OAuthTokens(access_token="", scopes=[])

    async def get_installation_token(self, installation_id: str) -> OAuthTokens:
        jwt_token = self._generate_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            data = response.json()

        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))

        return OAuthTokens(
            access_token=data["token"],
            expires_at=expires_at,
            scopes=list(data.get("permissions", {}).keys()),
        )

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        raise NotImplementedError("Use get_installation_token instead")

    async def get_installation_info(self, tokens: OAuthTokens) -> InstallationInfo:
        jwt_token = self._generate_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/app/installations",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            installations = response.json()

        if not installations:
            raise ValueError("No installations found")

        install = installations[0]
        return InstallationInfo(
            external_org_id=str(install["account"]["id"]),
            external_org_name=install["account"]["login"],
            external_install_id=str(install["id"]),
            installed_by=None,
            permissions=install.get("permissions", {}),
            metadata={
                "account_type": install["account"]["type"],
                "repository_selection": install["repository_selection"],
            },
        )

    async def get_installation_by_id(self, installation_id: str) -> InstallationInfo:
        jwt_token = self._generate_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/app/installations/{installation_id}",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            install = response.json()

        return InstallationInfo(
            external_org_id=str(install["account"]["id"]),
            external_org_name=install["account"]["login"],
            external_install_id=str(install["id"]),
            installed_by=None,
            permissions=install.get("permissions", {}),
            metadata={
                "account_type": install["account"]["type"],
                "repository_selection": install["repository_selection"],
            },
        )

    async def revoke_tokens(self, tokens: OAuthTokens) -> bool:
        return True
