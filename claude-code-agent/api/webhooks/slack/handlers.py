"""Slack domain response handler."""

import os
import json
import subprocess
from typing import Optional
import structlog

from api.webhooks.slack.models import SlackRoutingMetadata
from api.webhooks.slack.errors import SlackResponseError, SlackErrorContext
from api.webhooks.slack.validation import validate_response_format

logger = structlog.get_logger()


class SlackWebhookHandler:
    """Main webhook handler - coordinates the webhook processing flow."""

    def __init__(self, webhook_config):
        self.config = webhook_config
        self.response_handler = SlackResponseHandler()

    async def verify_signature(self, request, body):
        """Verify Slack webhook signature."""
        from api.webhooks.slack.utils import verify_slack_signature
        await verify_slack_signature(request, body)

    def parse_payload(self, body: bytes, provider_name: str) -> dict:
        """Parse webhook payload."""
        payload = json.loads(body.decode())
        payload["provider"] = provider_name
        return payload

    async def validate_webhook(self, payload: dict):
        """Validate webhook using validation handler."""
        from api.webhooks.slack.validation import validate_slack_webhook
        return validate_slack_webhook(payload)

    async def match_command(self, payload: dict):
        """Match command from webhook payload."""
        from api.webhooks.slack.utils import match_slack_command
        from api.webhooks.slack.constants import FIELD_EVENT, FIELD_TYPE, DEFAULT_EVENT_TYPE

        # Extract event_type from payload
        event = payload.get(FIELD_EVENT, {})
        event_type = event.get(FIELD_TYPE, DEFAULT_EVENT_TYPE)

        return await match_slack_command(payload, event_type)

    async def send_immediate_response(self, payload: dict, command, event_type: str):
        """Send immediate response to Slack."""
        from api.webhooks.slack.utils import send_slack_immediate_response
        return await send_slack_immediate_response(payload, command, event_type)

    async def create_task(self, command, payload: dict, db, completion_handler: str):
        """Create task for processing."""
        from api.webhooks.slack.utils import create_slack_task
        return await create_slack_task(command, payload, db, completion_handler)


class SlackResponseHandler:
    async def post_response(
        self, 
        routing: SlackRoutingMetadata, 
        result: str,
        blocks: Optional[list] = None
    ) -> tuple[bool, Optional[dict]]:
        if not routing.channel_id:
            logger.error("slack_channel_missing", routing=routing.model_dump())
            return False, None

        token = os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            logger.error("slack_token_missing")
            return False, None

        is_valid, error_msg = validate_response_format(result, "slack")
        if not is_valid:
            logger.warning(
                "slack_response_format_invalid",
                error=error_msg,
                channel_id=routing.channel_id
            )

        # Try using slack_client first (supports blocks)
        try:
            from core.slack_client import slack_client
            slack_client.token = token
            slack_client.headers["Authorization"] = f"Bearer {token}"
            
            response = await slack_client.post_message(
                channel=routing.channel_id,
                text=result,
                blocks=blocks,
                thread_ts=routing.thread_ts
            )
            
            logger.info("slack_response_posted", channel=routing.channel_id, used_blocks=blocks is not None)
            return True, response
        except ImportError:
            # Fall back to curl if slack_client not available
            pass
        except Exception as e:
            logger.warning("slack_client_failed_fallback_to_curl", error=str(e))

        # Fallback to curl
        payload = {
            "channel": routing.channel_id,
            "text": result,
        }

        if routing.thread_ts:
            payload["thread_ts"] = routing.thread_ts
        
        if blocks:
            payload["blocks"] = blocks

        try:
            proc = subprocess.run(
                [
                    "curl", "-s", "-X", "POST",
                    "https://slack.com/api/chat.postMessage",
                    "-H", f"Authorization: Bearer {token}",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if proc.returncode == 0:
                response = json.loads(proc.stdout)
                if response.get("ok"):
                    logger.info("slack_response_posted", channel=routing.channel_id)
                    return True, response
                else:
                    logger.error("slack_api_error", error=response.get("error"))
                    return False, None
            return False, None
        except Exception as e:
            context = SlackErrorContext(channel_id=routing.channel_id)
            raise SlackResponseError(f"Failed to post response: {str(e)}", context=context)


slack_response_handler = SlackResponseHandler()
