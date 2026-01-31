import hashlib
import hmac
import time

from config import get_settings
from middleware.error_handler import WebhookValidationError


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
