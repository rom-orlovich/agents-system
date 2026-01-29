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
