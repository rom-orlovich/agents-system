"""Webhook routers registration."""

from fastapi import APIRouter
from .github import router as github_router
from .jira import router as jira_router
from .slack import router as slack_router
from .sentry import router as sentry_router

router = APIRouter()

# Register all webhook routers (OLD pattern: one router per provider)
router.include_router(github_router, prefix="/webhooks")
router.include_router(jira_router, prefix="/webhooks")
router.include_router(slack_router, prefix="/webhooks")
router.include_router(sentry_router, prefix="/webhooks")
