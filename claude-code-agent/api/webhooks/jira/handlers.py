"""Jira domain response handler."""

import os
import json
import base64
import subprocess
from pathlib import Path
import structlog

from api.webhooks.jira.models import JiraRoutingMetadata
from api.webhooks.jira.errors import JiraResponseError, JiraErrorContext

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


class JiraResponseHandler:
    async def post_response(self, routing: JiraRoutingMetadata, result: str) -> bool:
        if not routing.issue_key:
            logger.error("jira_ticket_key_missing", routing=routing.model_dump())
            return False

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
                return True
        except FileNotFoundError as e:
            script_error = e
            logger.debug("jira_script_not_found", error=str(e))
        except Exception as e:
            script_error = e
            logger.warning("jira_script_failed", error=str(e))

        try:
            success = await self._post_via_api(routing.issue_key, result)
            if success:
                logger.info("jira_response_posted", ticket=routing.issue_key)
                return True
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

    async def _post_via_api(self, ticket_key: str, result: str) -> bool:
        base_url = os.environ.get("JIRA_BASE_URL")
        email = os.environ.get("JIRA_USER_EMAIL")
        token = os.environ.get("JIRA_API_TOKEN")

        if not all([base_url, email, token]):
            logger.error("jira_credentials_missing")
            return False

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
            return proc.returncode == 0
        except Exception as e:
            logger.error("jira_api_failed", error=str(e))
            return False


jira_response_handler = JiraResponseHandler()
