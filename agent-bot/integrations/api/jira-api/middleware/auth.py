"""Authentication middleware for Jira API."""

from typing import Callable
from fastapi import Request, status
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


class AuthMiddleware:
    """Validates Jira API credentials."""

    def __init__(self, app: Callable, api_key: str) -> None:
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        """Process request with auth validation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        if request.url.path in ["/health", "/metrics"]:
            await self.app(scope, receive, send)
            return

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing Authorization header"},
            )
            await response(scope, receive, send)
            return

        if not auth_header.startswith("Bearer "):
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid Authorization format"},
            )
            await response(scope, receive, send)
            return

        api_key = auth_header.replace("Bearer ", "")

        if api_key != self.api_key:
            logger.warning("invalid_api_key_attempt")
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
