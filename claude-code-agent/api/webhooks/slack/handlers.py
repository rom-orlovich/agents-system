"""Slack domain response handler."""

import os
import json
import subprocess
from pathlib import Path
import structlog

from api.webhooks.slack.models import SlackRoutingMetadata
from api.webhooks.slack.errors import SlackResponseError, SlackErrorContext

logger = structlog.get_logger()


def validate_response_format(result: str, format_type: str) -> tuple[bool, str]:
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        script_path = project_root / "scripts" / "validate-response-format.sh"

        if not script_path.exists():
            logger.warning("response_format_validation_script_not_found", script_path=str(script_path))
            return True, ""

        input_text = f"{format_type}\n{result}"

        validation_result = subprocess.run(
            [str(script_path)],
            input=input_text,
            text=True,
            capture_output=True,
            timeout=5,
            cwd=str(project_root)
        )

        if validation_result.returncode != 0:
            error_msg = validation_result.stderr.strip() or "Format validation failed"
            logger.warning("response_format_validation_failed", format_type=format_type, error=error_msg)
            return False, error_msg

        return True, ""
    except Exception as e:
        logger.error("response_format_validation_error", error=str(e), format_type=format_type)
        return True, ""


class SlackResponseHandler:
    async def post_response(self, routing: SlackRoutingMetadata, result: str) -> bool:
        if not routing.channel_id:
            logger.error("slack_channel_missing", routing=routing.model_dump())
            return False

        token = os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            logger.error("slack_token_missing")
            return False

        is_valid, error_msg = validate_response_format(result, "slack")
        if not is_valid:
            logger.warning(
                "slack_response_format_invalid",
                error=error_msg,
                channel_id=routing.channel_id
            )

        payload = {
            "channel": routing.channel_id,
            "text": result,
        }

        if routing.thread_ts:
            payload["thread_ts"] = routing.thread_ts

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
                    return True
                else:
                    logger.error("slack_api_error", error=response.get("error"))
                    return False
            return False
        except Exception as e:
            context = SlackErrorContext(channel_id=routing.channel_id)
            raise SlackResponseError(f"Failed to post response: {str(e)}", context=context)


slack_response_handler = SlackResponseHandler()
