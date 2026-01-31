import hashlib
import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

from config import get_settings
from middleware.error_handler import WebhookValidationError

logger = structlog.get_logger(__name__)


def validate_jira_signature(payload: bytes, signature: str | None) -> None:
    settings = get_settings()

    if not settings.jira_webhook_secret:
        return

    if not signature:
        raise WebhookValidationError("Missing X-Hub-Signature header")

    expected_signature = hmac.new(
        settings.jira_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise WebhookValidationError("Invalid signature")


class JiraAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ["/health", "/"]:
            return await call_next(request)

        if not request.url.path.startswith("/webhooks/jira"):
            return await call_next(request)

        body = await request.body()
        signature = request.headers.get("x-hub-signature")

        logger.debug(
            "jira_auth_validating",
            path=request.url.path,
            has_signature=signature is not None,
        )

        validate_jira_signature(body, signature)

        async def receive():
            return {"type": "http.request", "body": body}

        request = Request(request.scope, receive)
        return await call_next(request)
