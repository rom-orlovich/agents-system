"""Authentication middleware for Sentry API."""

from typing import Callable
from fastapi import Request, status
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


class AuthMiddleware:
    """Validates Sentry auth tokens."""

    def __init__(self, app: Callable, auth_token: str) -> None:
        self.app = app
        self.auth_token = auth_token

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

        token = auth_header.replace("Bearer ", "")

        if token != self.auth_token:
            logger.warning("invalid_sentry_token_attempt")
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid auth token"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
