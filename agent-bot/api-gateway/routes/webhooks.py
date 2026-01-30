"""Webhook routes."""

from fastapi import APIRouter, Request, HTTPException
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/github")
async def github_webhook(request: Request) -> dict[str, str]:
    """Handle GitHub webhooks."""
    logger.info("github_webhook_received")
    return {"status": "received", "source": "github"}


@router.post("/jira")
async def jira_webhook(request: Request) -> dict[str, str]:
    """Handle Jira webhooks."""
    logger.info("jira_webhook_received")
    return {"status": "received", "source": "jira"}


@router.post("/slack")
async def slack_webhook(request: Request) -> dict[str, str]:
    """Handle Slack webhooks."""
    logger.info("slack_webhook_received")
    return {"status": "received", "source": "slack"}


@router.post("/sentry")
async def sentry_webhook(request: Request) -> dict[str, str]:
    """Handle Sentry webhooks."""
    logger.info("sentry_webhook_received")
    return {"status": "received", "source": "sentry"}
