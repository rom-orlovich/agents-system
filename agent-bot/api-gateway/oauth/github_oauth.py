import httpx
import structlog
from oauth.models import GitHubOAuthResponse, GitHubInstallation

logger = structlog.get_logger()


class GitHubOAuthHandler:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
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
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            logger.error("github_oauth_error", error=data.get("error"))
            raise ValueError(f"GitHub OAuth error: {data.get('error')}")

        return GitHubOAuthResponse(**data)

    async def get_installation(self, access_token: str) -> GitHubInstallation:
        logger.info("fetching_github_installation")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/user/installations",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("installations"):
            raise ValueError("No GitHub installations found")

        installation = data["installations"][0]

        return GitHubInstallation(
            installation_id=installation["id"],
            account_login=installation["account"]["login"],
            account_id=installation["account"]["id"],
            repository_selection=installation.get("repository_selection", "all"),
            permissions=installation.get("permissions", {}),
        )
