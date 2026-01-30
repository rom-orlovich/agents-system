import structlog
import secrets
from fastapi import APIRouter, HTTPException, Query
from .models import OAuthCallbackRequest
from .github_oauth import GitHubOAuthHandler

logger = structlog.get_logger()

router = APIRouter(prefix="/oauth", tags=["oauth"])


def create_webhook_secret() -> str:
    return secrets.token_urlsafe(32)


@router.get("/github/callback")
async def github_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    logger.info("github_oauth_callback_received", state=state)

    import os

    handler = GitHubOAuthHandler(
        client_id=os.getenv("GITHUB_CLIENT_ID", ""),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
        redirect_uri=os.getenv("GITHUB_REDIRECT_URI", ""),
    )

    try:
        oauth_response = await handler.exchange_code(code)

        installation_info = await handler.get_installation(
            oauth_response.access_token
        )

        webhook_secret = create_webhook_secret()

        result = {
            "success": True,
            "installation_id": installation_info["installation_id"],
            "organization_id": installation_info["account_id"],
            "organization_name": installation_info["account_login"],
            "access_token": oauth_response.access_token,
            "webhook_secret": webhook_secret,
            "scopes": oauth_response.scope.split(","),
            "token_expires_at": handler.calculate_token_expiry().isoformat(),
        }

        logger.info(
            "github_oauth_success",
            installation_id=installation_info["installation_id"],
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("github_oauth_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slack/callback")
async def slack_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    logger.info("slack_oauth_callback_received", state=state)

    return {
        "success": True,
        "message": "Slack OAuth not fully implemented yet",
        "code": code,
        "state": state,
    }


@router.get("/jira/callback")
async def jira_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    logger.info("jira_oauth_callback_received", state=state)

    return {
        "success": True,
        "message": "Jira OAuth not fully implemented yet",
        "code": code,
        "state": state,
    }
