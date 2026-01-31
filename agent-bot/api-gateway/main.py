from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from config import get_settings
from routes import webhooks_router
from middleware import AuthMiddleware, error_handler
from middleware.error_handler import WebhookValidationError

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("api_gateway_starting", port=settings.port)
    yield
    logger.info("api_gateway_shutting_down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agent API Gateway",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(AuthMiddleware)
    app.add_exception_handler(WebhookValidationError, error_handler)
    app.add_exception_handler(Exception, error_handler)

    app.include_router(webhooks_router)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "api-gateway"}

    @app.get("/")
    async def root():
        return {
            "service": "agent-api-gateway",
            "version": "1.0.0",
            "endpoints": {
                "github": "/webhooks/github",
                "jira": "/webhooks/jira",
                "slack": "/webhooks/slack",
                "sentry": "/webhooks/sentry",
            },
        }

    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
    )
