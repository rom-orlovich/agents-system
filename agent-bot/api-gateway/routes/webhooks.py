from fastapi import APIRouter

from webhooks import github_router, jira_router, slack_router, sentry_router

router = APIRouter()

router.include_router(github_router)
router.include_router(jira_router)
router.include_router(slack_router)
router.include_router(sentry_router)
