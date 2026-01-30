import secrets
from urllib.parse import urlencode

import httpx
import structlog

from .models import (
    OAuthState,
    GitHubTokenResponse,
    GitHubInstallationInfo,
)

logger = structlog.get_logger()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


class GitHubOAuthError(Exception):
    def __init__(self, error: str, description: str):
        self.error = error
        self.description = description
        super().__init__(f"{error}: {description}")


class GitHubOAuthHandler:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http_client = http_client

    def get_authorization_url(
        self,
        state: OAuthState,
        scopes: list[str] | None = None,
    ) -> str:
        default_scopes = ["repo", "read:org", "read:user"]
        final_scopes = scopes or default_scopes

        params = {
            "client_id": self._client_id,
            "redirect_uri": state.redirect_uri,
            "scope": ",".join(final_scopes),
            "state": state.to_encoded(),
        }

        return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> GitHubTokenResponse:
        logger.info("exchanging_github_code")

        client = self._get_client()
        response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )

        data = response.json()

        if response.status_code != 200 or "error" in data:
            error = data.get("error", "unknown_error")
            description = data.get("error_description", "Unknown error")
            logger.error(
                "github_code_exchange_failed",
                error=error,
                description=description,
            )
            raise GitHubOAuthError(error, description)

        logger.info("github_code_exchanged_successfully")
        return GitHubTokenResponse.model_validate(data)

    async def get_authenticated_user(
        self, access_token: str
    ) -> dict[str, str]:
        client = self._get_client()
        response = await client.get(
            f"{GITHUB_API_URL}/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )

        if response.status_code != 200:
            raise GitHubOAuthError(
                "user_fetch_failed",
                f"Failed to fetch user: {response.status_code}",
            )

        data = response.json()
        return {
            "id": str(data["id"]),
            "login": data["login"],
            "email": data.get("email", ""),
        }

    def validate_state(self, encoded_state: str) -> OAuthState:
        try:
            return OAuthState.from_encoded(encoded_state)
        except Exception as e:
            logger.error("invalid_oauth_state", error=str(e))
            raise ValueError("Invalid OAuth state")

    def generate_webhook_secret(self) -> str:
        return secrets.token_hex(32)

    def _get_client(self) -> httpx.AsyncClient:
        if self._http_client:
            return self._http_client
        return httpx.AsyncClient()
