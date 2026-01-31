import hashlib
import hmac

from config import get_settings
from middleware.error_handler import WebhookValidationError


def validate_github_signature(payload: bytes, signature: str | None) -> None:
    settings = get_settings()

    if not settings.github_webhook_secret:
        return

    if not signature:
        raise WebhookValidationError("Missing X-Hub-Signature-256 header")

    if not signature.startswith("sha256="):
        raise WebhookValidationError("Invalid signature format")

    expected_signature = hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    received_signature = signature[7:]

    if not hmac.compare_digest(expected_signature, received_signature):
        raise WebhookValidationError("Invalid signature")
