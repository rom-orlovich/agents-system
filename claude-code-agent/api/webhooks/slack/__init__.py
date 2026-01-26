"""
Slack webhook module.
Exports router and validation functions.
"""

from api.webhooks.slack.routes import router
from api.webhooks.slack.validation import validate_slack_webhook, SlackWebhookPayload

__all__ = ["router", "validate_slack_webhook", "SlackWebhookPayload"]
