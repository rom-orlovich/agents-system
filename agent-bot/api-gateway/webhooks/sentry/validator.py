import hashlib
import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
import structlog

from config import get_settings
from middleware.error_handler import WebhookValidationError

logger = structlog.get_logger(__name__)


def validate_sentry_signature(payload: bytes, signature: str | None) -> None:
    settings = get_settings()

    if not settings.sentry_client_secret:
        return

    if not signature:
        raise WebhookValidationError("Missing Sentry-Hook-Signature header")

    expected_signature = hmac.new(
        settings.sentry_client_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise WebhookValidationError("Invalid signature")


class SentryAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ["/health", "/"]:
            return await call_next(request)

        if not request.url.path.startswith("/webhooks/sentry"):
            return await call_next(request)

        body = await request.body()
        signature = request.headers.get("sentry-hook-signature")

        logger.debug(
            "sentry_auth_validating",
            path=request.url.path,
            has_signature=signature is not None,
        )

        try:
            validate_sentry_signature(body, signature)
        except WebhookValidationError as e:
            logger.warning("sentry_signature_validation_failed", error=str(e))
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": str(e)},
            )

        async def receive():
            return {"type": "http.request", "body": body}

        request = Request(request.scope, receive)
        return await call_next(request)
