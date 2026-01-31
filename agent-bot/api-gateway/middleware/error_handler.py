from fastapi import Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)


class WebhookValidationError(Exception):
    pass


async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, WebhookValidationError):
        logger.warning("webhook_validation_failed", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=401,
            content={"error": "Webhook validation failed", "detail": str(exc)},
        )

    logger.exception("unhandled_error", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
