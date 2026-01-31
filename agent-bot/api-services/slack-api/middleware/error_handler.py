from fastapi import Request
from fastapi.responses import JSONResponse
import httpx
import structlog

from client.slack_client import SlackAPIError

logger = structlog.get_logger(__name__)


async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, SlackAPIError):
        logger.error("slack_api_error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=400,
            content={"error": "Slack API error", "detail": str(exc)},
        )

    if isinstance(exc, httpx.HTTPStatusError):
        logger.error(
            "http_error",
            status_code=exc.response.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.response.status_code,
            content={"error": "HTTP error", "detail": exc.response.text},
        )

    logger.exception("unhandled_error", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
