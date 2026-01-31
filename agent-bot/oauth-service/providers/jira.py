import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import httpx
import structlog

from config.settings import Settings

from .base import InstallationInfo, OAuthProvider, OAuthTokens

logger = structlog.get_logger(__name__)

DEFAULT_SCOPES = [
    "read:jira-work",
    "write:jira-work",
    "read:jira-user",
    "offline_access",
]


class JiraOAuthProvider(OAuthProvider):
    def __init__(self, settings: Settings):
        self.client_id = settings.jira_client_id
        self.client_secret = settings.jira_client_secret
        self.redirect_uri = f"{settings.base_url}/oauth/callback/jira"
        self.scopes = DEFAULT_SCOPES
        self._code_verifiers: dict[str, str] = {}

    def _generate_code_verifier(self) -> str:
        return secrets.token_urlsafe(32)

    def _generate_code_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    def get_authorization_url(self, state: str) -> str:
        code_verifier = self._generate_code_verifier()
        self._code_verifiers[state] = code_verifier
        code_challenge = self._generate_code_challenge(code_verifier)
        scope_str = " ".join(self.scopes)

        return (
            f"https://auth.atlassian.com/authorize"
            f"?audience=api.atlassian.com"
            f"&client_id={self.client_id}"
            f"&scope={scope_str}"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
            f"&response_type=code"
            f"&prompt=consent"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
        )

    def get_code_verifier(self, state: str) -> str | None:
        return self._code_verifiers.pop(state, None)

    async def exchange_code(self, code: str, state: str) -> OAuthTokens:
        code_verifier = self.get_code_verifier(state)

        payload: dict[str, str] = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        if code_verifier:
            payload["code_verifier"] = code_verifier

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            scopes=data.get("scope", "").split(" "),
        )

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            data = response.json()

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_at=expires_at,
        )

    async def get_installation_info(self, tokens: OAuthTokens) -> InstallationInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            response.raise_for_status()
            resources = response.json()

        if not resources:
            raise ValueError("No accessible Jira sites found")

        site = resources[0]
        return InstallationInfo(
            external_org_id=site["id"],
            external_org_name=site["name"],
            external_install_id=None,
            installed_by=None,
            permissions={scope: "granted" for scope in tokens.scopes or []},
            metadata={
                "url": site["url"],
                "scopes": site.get("scopes", []),
                "avatar_url": site.get("avatarUrl"),
            },
        )

    async def revoke_tokens(self, tokens: OAuthTokens) -> bool:
        return True
