from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx
import structlog

from .routes import router
from middleware import AuthMiddleware, error_handler
from client.slack_client import SlackAPIError

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("slack_api_starting")
    yield
    logger.info("slack_api_shutting_down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Slack API Service",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(AuthMiddleware)
    app.add_exception_handler(SlackAPIError, error_handler)
    app.add_exception_handler(httpx.HTTPStatusError, error_handler)
    app.add_exception_handler(Exception, error_handler)

    app.include_router(router)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "slack-api"}

    return app
