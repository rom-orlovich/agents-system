from fastapi import APIRouter, Query, HTTPException
from oauth.github_oauth import GitHubOAuthHandler
from oauth.models import GitHubOAuthResponse
import structlog
import secrets

logger = structlog.get_logger()
router = APIRouter(prefix="/oauth", tags=["oauth"])


def create_webhook_secret() -> str:
    return secrets.token_urlsafe(32)


@router.get("/github/callback")
async def github_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
) -> dict[str, str | int | dict[str, str]]:
    logger.info("github_oauth_callback", state=state)

    try:
        handler = GitHubOAuthHandler(
            client_id="github_client_id",
            client_secret="github_client_secret",
            redirect_uri="http://localhost:8000/oauth/github/callback",
        )

        oauth_response = await handler.exchange_code(code)
        installation_info = await handler.get_installation(oauth_response.access_token)

        webhook_secret = create_webhook_secret()

        return {
            "success": True,
            "installation_id": installation_info.installation_id,
            "organization_id": str(installation_info.account_id),
            "organization_name": installation_info.account_login,
            "webhook_secret": webhook_secret,
            "scopes": oauth_response.scope.split(","),
        }

    except Exception as e:
        logger.error("github_oauth_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/slack/callback")
async def slack_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
) -> dict[str, str | bool]:
    logger.info("slack_oauth_callback", state=state)
    return {"success": True, "message": "Slack OAuth not fully implemented"}


@router.get("/jira/callback")
async def jira_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
) -> dict[str, str | bool]:
    logger.info("jira_oauth_callback", state=state)
    return {"success": True, "message": "Jira OAuth not fully implemented"}
