import httpx
import structlog
from oauth.models import SlackOAuthResponse
from oauth.exceptions import SlackAuthenticationError

logger = structlog.get_logger()


class SlackOAuthHandler:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_url = "https://slack.com/api/oauth.v2.access"
        self.api_base = "https://slack.com/api"

    async def exchange_code(self, code: str) -> SlackOAuthResponse:
        logger.info("exchanging_slack_code")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error("slack_oauth_http_error", status=e.response.status_code)
                raise SlackAuthenticationError(f"Slack OAuth HTTP error: {e}")
            except Exception as e:
                logger.error("slack_oauth_error", error=str(e))
                raise SlackAuthenticationError(f"Slack OAuth error: {e}")

        if not data.get("ok"):
            error = data.get("error", "unknown_error")
            logger.error("slack_oauth_failed", error=error)
            raise SlackAuthenticationError(f"Slack OAuth failed: {error}")

        return SlackOAuthResponse(
            team_id=data["team"]["id"],
            team_name=data["team"]["name"],
            access_token=data["access_token"],
            bot_user_id=data["bot_user_id"],
            scopes=data["scope"].split(","),
            expires_at=None,
        )

    async def get_team_info(self, access_token: str) -> dict[str, str]:
        logger.info("fetching_slack_team_info")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_base}/team.info",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error("slack_team_info_http_error", status=e.response.status_code)
                raise SlackAuthenticationError(f"Slack team info HTTP error: {e}")
            except Exception as e:
                logger.error("slack_team_info_error", error=str(e))
                raise SlackAuthenticationError(f"Slack team info error: {e}")

        if not data.get("ok"):
            error = data.get("error", "unknown_error")
            logger.error("slack_team_info_failed", error=error)
            raise SlackAuthenticationError(f"Slack team info failed: {error}")

        team = data["team"]
        return {
            "id": team["id"],
            "name": team["name"],
            "domain": team.get("domain", ""),
        }
