"""Jira domain response handler."""

import os
import json
import base64
import subprocess
from typing import Optional
import structlog

from api.webhooks.jira.models import JiraRoutingMetadata
from api.webhooks.jira.errors import JiraResponseError, JiraErrorContext
from api.webhooks.jira.validation import validate_response_format

logger = structlog.get_logger()


class JiraWebhookHandler:
    """Main webhook handler - coordinates the webhook processing flow."""

    def __init__(self, webhook_config):
        self.config = webhook_config
        self.response_handler = JiraResponseHandler()

    async def verify_signature(self, request, body):
        """Verify Jira webhook signature."""
        from api.webhooks.jira.utils import verify_jira_signature
        await verify_jira_signature(request, body)

    def parse_payload(self, body: bytes, provider_name: str) -> dict:
        """Parse webhook payload."""
        payload = json.loads(body.decode())
        payload["provider"] = provider_name
        return payload

    async def validate_webhook(self, payload: dict):
        """Validate webhook using validation handler."""
        from api.webhooks.jira.validation import validate_jira_webhook
        return validate_jira_webhook(payload)

    async def match_command(self, payload: dict, event_type: str):
        """Match command from webhook payload."""
        from api.webhooks.jira.utils import match_jira_command
        return await match_jira_command(payload, event_type)

    async def send_immediate_response(self, payload: dict, command, task_id: str):
        """Send immediate response to Jira."""
        from api.webhooks.jira.utils import send_jira_immediate_response
        return await send_jira_immediate_response(payload, command, task_id)

    async def create_task(self, command, payload: dict, db, completion_handler: str):
        """Create task for processing."""
        from api.webhooks.jira.utils import create_jira_task
        return await create_jira_task(command, payload, db, completion_handler)


class JiraResponseHandler:
    async def post_response(self, routing: JiraRoutingMetadata, result: str) -> tuple[bool, Optional[dict]]:
        if not routing.issue_key:
            logger.error("jira_ticket_key_missing", routing=routing.model_dump())
            return False, None

        is_valid, error_msg = validate_response_format(result, "jira")
        if not is_valid:
            logger.warning(
                "jira_response_format_invalid",
                error=error_msg,
                ticket_key=routing.issue_key
            )

        script_error = None
        try:
            success = await self._post_via_script(routing.issue_key, result)
            if success:
                logger.info("jira_response_posted", ticket=routing.issue_key)
                return True, None  # Script doesn't return comment ID
        except FileNotFoundError as e:
            script_error = e
            logger.debug("jira_script_not_found", error=str(e))
        except Exception as e:
            script_error = e
            logger.warning("jira_script_failed", error=str(e))

        try:
            success, response = await self._post_via_api(routing.issue_key, result)
            if success:
                logger.info("jira_response_posted", ticket=routing.issue_key)
                return True, response
            else:
                context = JiraErrorContext(issue_key=routing.issue_key)
                raise JiraResponseError("API posting returned False", context=context)
        except JiraResponseError:
            raise
        except Exception as e:
            context = JiraErrorContext(issue_key=routing.issue_key)
            raise JiraResponseError(
                f"Failed to post response: {str(e)} (script error: {script_error})",
                context=context
            )

    async def _post_via_script(self, ticket_key: str, result: str) -> bool:
        script_path = ".claude/skills/jira-operations/scripts/post_comment.sh"

        proc = subprocess.run(
            [script_path, ticket_key, result],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.environ.get("AGENT_HOME", ".")
        )

        if proc.returncode == 0:
            return True
        else:
            logger.error("jira_script_failed", stderr=proc.stderr)
            return False

    async def _post_via_api(self, ticket_key: str, result: str) -> tuple[bool, Optional[dict]]:
        base_url = os.environ.get("JIRA_BASE_URL")
        email = os.environ.get("JIRA_USER_EMAIL")
        token = os.environ.get("JIRA_API_TOKEN")

        if not all([base_url, email, token]):
            logger.error("jira_credentials_missing")
            return False, None

        auth = base64.b64encode(f"{email}:{token}".encode()).decode()
        url = f"{base_url}/rest/api/3/issue/{ticket_key}/comment"

        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": result}]
                    }
                ]
            }
        }

        try:
            proc = subprocess.run(
                [
                    "curl", "-s", "-X", "POST", url,
                    "-H", f"Authorization: Basic {auth}",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(body)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            if proc.returncode == 0:
                try:
                    response = json.loads(proc.stdout) if proc.stdout else None
                    return True, response
                except json.JSONDecodeError:
                    return True, None
            return False, None
        except Exception as e:
            logger.error("jira_api_failed", error=str(e))
            return False, None


jira_response_handler = JiraResponseHandler()
