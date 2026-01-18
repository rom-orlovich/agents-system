"""
Webhook Server
==============
FastAPI server that receives webhooks from Jira, Sentry, and GitHub.
"""

import uvicorn
from fastapi import FastAPI

from webhook_server.routes import github, jira, sentry
from shared.config import get_settings
from shared.utils import setup_logging

app = FastAPI(
    title="Claude Agent Webhook Server",
    description="Receives webhooks and queues tasks for Claude agents",
    version="0.1.0",
)

# Include routers
app.include_router(jira.router, prefix="/jira-webhook", tags=["jira"])
app.include_router(sentry.router, prefix="/sentry-webhook", tags=["sentry"])
app.include_router(github.router, prefix="/github-webhook", tags=["github"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Claude Agent Webhook Server",
        "endpoints": [
            "/jira-webhook",
            "/sentry-webhook",
            "/github-webhook",
            "/health",
        ],
    }


def main():
    """Run the webhook server."""
    setup_logging()
    settings = get_settings()
    uvicorn.run(
        "webhook_server.main:app",
        host=settings.webhook.host,
        port=settings.webhook.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
