"""
Slack webhook validation.
Pydantic models and validation logic for Slack webhooks.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel
from core.webhook_validation import (
    WebhookValidationResult,
    extract_command,
    validate_command,
)
from api.webhooks.slack.utils import extract_slack_text


class SlackWebhookPayload(BaseModel):
    """Slack webhook payload model."""
    event: Optional[Dict[str, Any]] = None
    text: Optional[str] = None

    def extract_text(self) -> str:
        event_text_raw = self.event.get("text", "") if self.event else ""
        text_raw = self.text or ""
        event_text = extract_slack_text(event_text_raw)
        text = extract_slack_text(text_raw)
        return event_text or text

    def validate(self) -> WebhookValidationResult:
        """Validate Slack webhook payload."""
        text = self.extract_text()
        
        if not text:
            return WebhookValidationResult.success()
        
        command = extract_command(text)
        is_valid, error_msg = validate_command(command)
        
        if not is_valid:
            return WebhookValidationResult.failure(f"{error_msg} in Slack message")
        
        return WebhookValidationResult.success()


def validate_slack_webhook(payload: Dict[str, Any]) -> WebhookValidationResult:
    """Validate Slack webhook payload."""
    try:
        slack_payload = SlackWebhookPayload(**payload)
        return slack_payload.validate()
    except Exception as e:
        return WebhookValidationResult.failure(f"Invalid Slack webhook payload: {e}")
