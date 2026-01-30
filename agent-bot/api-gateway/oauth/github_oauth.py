import httpx
import structlog
from fastapi import HTTPException
from .models import OAuthCallbackRequest, GitHubOAuthResponse
from datetime import datetime, timezone, timedelta

logger = structlog.get_logger()


class GitHubOAuthHandler:
    def __init__(
        self, client_id: str, client_secret: str, redirect_uri: str
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_url = "https://github.com/login/oauth/access_token"
        self.api_base = "https://api.github.com"

    async def exchange_code(self, code: str) -> GitHubOAuthResponse:
        logger.info("exchanging_github_code")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                logger.error(
                    "github_token_exchange_failed", status=response.status_code
                )
                raise HTTPException(
                    status_code=400, detail="Failed to exchange code"
                )

            data = response.json()
            return GitHubOAuthResponse(**data)

    async def get_installation(self, access_token: str) -> dict:
        logger.info("fetching_github_installation")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/user/installations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )

            if response.status_code != 200:
                logger.error(
                    "github_installation_fetch_failed",
                    status=response.status_code,
                )
                raise HTTPException(
                    status_code=400, detail="Failed to fetch installation"
                )

            data = response.json()
            installations = data.get("installations", [])

            if not installations:
                raise HTTPException(
                    status_code=404, detail="No installation found"
                )

            installation = installations[0]

            return {
                "installation_id": str(installation["id"]),
                "account_id": str(installation["account"]["id"]),
                "account_login": installation["account"]["login"],
                "target_type": installation["target_type"],
            }

    def calculate_token_expiry(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(hours=8)
