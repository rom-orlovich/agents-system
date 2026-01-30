"""Authentication middleware for GitHub API."""

from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


class AuthMiddleware:
    """Validates GitHub API tokens."""

    def __init__(self, app: Callable, valid_token: str) -> None:
        self.app = app
        self.valid_token = valid_token

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

        if token != self.valid_token:
            logger.warning("invalid_token_attempt", token_prefix=token[:8])
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
