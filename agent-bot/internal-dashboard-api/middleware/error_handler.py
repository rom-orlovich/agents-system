from fastapi import Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)


async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
