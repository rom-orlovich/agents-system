import hashlib
import hmac

from config import get_settings
from middleware.error_handler import WebhookValidationError


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
