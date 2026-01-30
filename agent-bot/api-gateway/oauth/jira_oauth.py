import httpx
import structlog
from oauth.models import JiraOAuthResponse
from oauth.exceptions import JiraAuthenticationError

logger = structlog.get_logger()


class JiraOAuthHandler:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_url = "https://auth.atlassian.com/oauth/token"
        self.api_base = "https://api.atlassian.com"

    async def exchange_code(self, code: str) -> JiraOAuthResponse:
        logger.info("exchanging_jira_code")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_url,
                    json={
                        "grant_type": "authorization_code",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error("jira_oauth_http_error", status=e.response.status_code)
                raise JiraAuthenticationError(f"Jira OAuth HTTP error: {e}")
            except Exception as e:
                logger.error("jira_oauth_error", error=str(e))
                raise JiraAuthenticationError(f"Jira OAuth error: {e}")

        if "error" in data:
            error = data.get("error", "unknown_error")
            logger.error("jira_oauth_failed", error=error)
            raise JiraAuthenticationError(f"Jira OAuth failed: {error}")

        resources = await self.get_accessible_resources(data["access_token"])
        if not resources:
            raise JiraAuthenticationError("No accessible Jira resources found")

        first_resource = resources[0]

        return JiraOAuthResponse(
            cloud_id=first_resource["id"],
            site_url=first_resource["url"],
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            scopes=data["scope"].split(),
            expires_at=data.get("expires_in"),
        )

    async def get_accessible_resources(self, access_token: str) -> list[dict[str, str]]:
        logger.info("fetching_jira_accessible_resources")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_base}/oauth/token/accessible-resources",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error("jira_resources_http_error", status=e.response.status_code)
                raise JiraAuthenticationError(f"Jira resources HTTP error: {e}")
            except Exception as e:
                logger.error("jira_resources_error", error=str(e))
                raise JiraAuthenticationError(f"Jira resources error: {e}")

        return data
