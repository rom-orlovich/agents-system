"""Webhook routers registration."""

from fastapi import APIRouter
from .github import router as github_router
from .jira import router as jira_router
from .slack import router as slack_router

router = APIRouter()

# Register all webhook routers
router.include_router(github_router, prefix="/webhooks")
router.include_router(jira_router, prefix="/webhooks")
router.include_router(slack_router, prefix="/webhooks")
