from fastapi import Request
from fastapi.responses import JSONResponse
import httpx
import structlog

logger = structlog.get_logger(__name__)


async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, httpx.HTTPStatusError):
        logger.error(
            "github_api_error",
            status_code=exc.response.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.response.status_code,
            content={
                "error": "GitHub API error",
                "detail": exc.response.text,
            },
        )

    logger.exception("unhandled_error", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
