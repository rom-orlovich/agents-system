import hashlib
import hmac
import json
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
import structlog

from config import get_settings
from middleware.error_handler import WebhookValidationError

logger = structlog.get_logger(__name__)


def validate_slack_signature(
    payload: bytes, signature: str | None, timestamp: str | None
) -> None:
    settings = get_settings()

    if not settings.slack_signing_secret:
        return

    if not signature or not timestamp:
        raise WebhookValidationError("Missing Slack signature headers")

    current_time = int(time.time())
    request_time = int(timestamp)
    if abs(current_time - request_time) > 60 * 5:
        raise WebhookValidationError("Request timestamp too old")

    sig_basestring = f"v0:{timestamp}:{payload.decode()}"
    expected_signature = (
        "v0="
        + hmac.new(
            settings.slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(expected_signature, signature):
        raise WebhookValidationError("Invalid signature")


class SlackAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ["/health", "/"]:
            return await call_next(request)

        if not request.url.path.startswith("/webhooks/slack"):
            return await call_next(request)

        body = await request.body()

        try:
            data = json.loads(body)
            if data.get("type") == "url_verification":

                async def receive():
                    return {"type": "http.request", "body": body}

                request = Request(request.scope, receive)
                return await call_next(request)
        except json.JSONDecodeError:
            pass

        signature = request.headers.get("x-slack-signature")
        timestamp = request.headers.get("x-slack-request-timestamp")

        logger.debug(
            "slack_auth_validating",
            path=request.url.path,
            has_signature=signature is not None,
            has_timestamp=timestamp is not None,
        )

        try:
            validate_slack_signature(body, signature, timestamp)
        except WebhookValidationError as e:
            logger.warning("slack_signature_validation_failed", error=str(e))
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": str(e)},
            )

        async def receive():
            return {"type": "http.request", "body": body}

        request = Request(request.scope, receive)
        return await call_next(request)
