"""GitHub domain response handler."""

import os
import json
import subprocess
from typing import Optional
import structlog

from api.webhooks.github.models import GitHubRoutingMetadata
from api.webhooks.github.errors import GitHubResponseError, GitHubErrorContext
from api.webhooks.github.validation import validate_response_format
from api.webhooks.github.metadata import extract_github_routing

logger = structlog.get_logger()

try:
    from core.github_client import github_client
except ImportError:
    github_client = None


def has_meaningful_response(result: str, message: str) -> bool:
    """Check if response has meaningful content."""
    return bool(
        (result and len(result.strip()) > 50) or
        (message and len(message.strip()) > 50 and message.strip() != "❌")
    )


def format_github_message(message: str, success: bool, cost_usd: float) -> str:
    """Format GitHub message with emoji, cost, and truncation."""
    if success:
        formatted = f"✅ {message}"
    else:
        formatted = "❌" if message == "❌" else f"❌ {message}"

    max_length = 4000 if success else 8000
    if len(formatted) > max_length:
        truncated = formatted[:max_length]
        last_period = truncated.rfind(".")
        last_newline = truncated.rfind("\n")
        truncate_at = max(last_period, last_newline)
        if truncate_at > max_length * 0.8:
            truncated = truncated[:truncate_at + 1]
        formatted = truncated + "\n\n... (message truncated)"

    if success and cost_usd > 0:
        formatted += f"\n\n💰 Cost: ${cost_usd:.4f}"

    return formatted


async def track_github_comment(comment_id: int | None) -> None:
    """Track GitHub comment ID in Redis to prevent infinite loops."""
    if comment_id:
        try:
            from core.database.redis_client import redis_client
            from api.webhooks.github.constants import REDIS_KEY_PREFIX_POSTED_COMMENT
            key = f"{REDIS_KEY_PREFIX_POSTED_COMMENT}{comment_id}"
            await redis_client._client.setex(key, 3600, "1")
            logger.debug("github_comment_id_tracked", comment_id=comment_id)
        except Exception as e:
            logger.warning("github_comment_id_tracking_failed", comment_id=comment_id, error=str(e))


async def add_error_reaction(payload: dict, task_id: str, error: str) -> None:
    """Add error reaction to GitHub comment."""
    original_comment_id = payload.get("comment", {}).get("id")
    if not original_comment_id:
        return

    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")

    if not owner or not repo_name:
        logger.warning("github_reaction_skipped_no_repo", task_id=task_id)
        return

    try:
        if github_client:
            github_client.token = github_client.token or os.getenv("GITHUB_TOKEN")
            if github_client.token:
                github_client.headers["Authorization"] = f"token {github_client.token}"
                await github_client.add_reaction(owner, repo_name, original_comment_id, reaction="-1")
                logger.info(
                    "github_error_reaction_added",
                    task_id=task_id,
                    comment_id=original_comment_id,
                    error_preview=error[:200] if error else None
                )
            else:
                logger.warning("github_reaction_skipped_no_token", comment_id=original_comment_id)
    except Exception as e:
        logger.warning("github_error_reaction_failed", task_id=task_id, comment_id=original_comment_id, error=str(e))


def get_command_requires_approval(command: str, webhook_config) -> bool:
    """Check if command requires approval from webhook config."""
    if not command or webhook_config is None:
        return False
    for cmd in webhook_config.commands:
        if cmd.name == command:
            return cmd.requires_approval
    return False


async def send_approval_notification(
    payload: dict,
    task_id: str,
    command: str,
    message: str | list | None,
    result: str | list | None,
    cost_usd: float
) -> None:
    """Send approval notification to Slack with action buttons."""
    from api.webhooks.slack.utils import extract_task_summary, build_task_completion_blocks
    from core.slack_client import slack_client
    from api.webhooks.github.constants import PROVIDER_NAME, DEFAULT_EVENT_TYPE

    # Defensive type conversion to prevent TypeError in extract_task_summary
    if isinstance(result, list):
        result = "\n".join(str(item) for item in result)
    elif result and not isinstance(result, str):
        result = str(result)

    if isinstance(message, list):
        message = "\n".join(str(item) for item in message)
    elif message and not isinstance(message, str):
        message = str(message)

    repo = payload.get("repository", {}).get("full_name", "")
    pr_number = payload.get("pull_request", {}).get("number") or payload.get("issue", {}).get("number")

    routing = {"repo": repo, "pr_number": pr_number}
    task_metadata = {"classification": payload.get("classification", "SIMPLE")}
    summary = extract_task_summary(result or message or "", task_metadata)

    blocks = build_task_completion_blocks(
        summary=summary,
        routing=routing,
        requires_approval=True,
        task_id=task_id or DEFAULT_EVENT_TYPE,
        cost_usd=cost_usd,
        command=command or "",
        source=PROVIDER_NAME
    )

    channel = payload.get("routing", {}).get("slack_channel") or os.getenv("SLACK_CHANNEL_AGENTS", "#ai-agent-activity")

    try:
        await slack_client.post_message(
            channel=channel,
            text=message[:200] if message else "Task completed",
            blocks=blocks
        )
        logger.info("github_slack_rich_notification_sent", task_id=task_id, channel=channel, has_buttons=True)
    except Exception as e:
        logger.warning("github_slack_rich_notification_failed", task_id=task_id, error=str(e))


async def handle_github_task_completion(
    payload: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0,
    task_id: str = None,
    command: str = None,
    result: str | list[str] | None = None,
    error: str = None,
    webhook_config = None
) -> bool:
    """Handle GitHub task completion - post response and notifications."""
    from api.webhooks.github.utils import send_slack_notification
    from api.webhooks.github.constants import PROVIDER_NAME

    # Convert result to string if needed
    if isinstance(result, list):
        result = "\n".join(str(item) for item in result)
    elif result and not isinstance(result, str):
        result = str(result)

    # Convert message to string if needed (prevents TypeError in downstream functions)
    if isinstance(message, list):
        message = "\n".join(str(item) for item in message)
    elif message and not isinstance(message, str):
        message = str(message)
    if not isinstance(message, str):
        message = ""

    has_meaningful = has_meaningful_response(result, message)

    if not success and error:
        await add_error_reaction(payload, task_id, error)

        if has_meaningful:
            logger.info("github_task_failed_but_response_already_posted", task_id=task_id, error_preview=error[:200] if error else None)
        else:
            logger.info("github_task_failed_no_new_comment", task_id=task_id, error_preview=error[:200] if error else None)

        comment_posted = False
    else:
        routing = extract_github_routing(payload)
        formatted_message = format_github_message(message, success, cost_usd)

        logger.info(
            "github_posting_final_response",
            task_id=task_id,
            repo=f"{routing.owner}/{routing.repo}",
            issue_or_pr=routing.issue_number or routing.pr_number,
            message_length=len(formatted_message)
        )

        handler = GitHubResponseHandler()
        try:
            comment_posted, response = await handler.post_response(routing, formatted_message)

            if comment_posted and response and isinstance(response, dict):
                comment_id = response.get("id")
                if comment_id:
                    await track_github_comment(comment_id)
                    logger.info(
                        "github_final_response_posted",
                        task_id=task_id,
                        comment_id=comment_id
                    )
        except Exception as e:
            logger.error("github_handler_post_failed", error=str(e), task_id=task_id)
            comment_posted = False

    if get_command_requires_approval(command, webhook_config):
        await send_approval_notification(payload, task_id, command, message, result, cost_usd)

    await send_slack_notification(
        task_id=task_id,
        webhook_source=PROVIDER_NAME,
        command=command,
        success=success,
        result=result,
        error=error
    )

    return comment_posted


class GitHubResponseHandler:
    async def post_response(self, routing: GitHubRoutingMetadata, result: str) -> tuple[bool, Optional[dict]]:
        if not routing.owner or not routing.repo:
            logger.error("github_routing_missing", routing=routing.model_dump())
            return False, None

        if not routing.pr_number and not routing.issue_number:
            logger.error("github_no_pr_or_issue", routing=routing.model_dump())
            return False, None

        try:
            if routing.pr_number:
                return await self._post_to_pr(routing, result)
            else:
                return await self._post_to_issue(routing, result)
        except GitHubResponseError:
            raise
        except Exception as e:
            context = GitHubErrorContext(
                repo=f"{routing.owner}/{routing.repo}",
                issue_number=routing.issue_number,
                pr_number=routing.pr_number
            )
            raise GitHubResponseError(f"Failed to post response: {str(e)}", context=context)

    async def _post_to_pr(self, routing: GitHubRoutingMetadata, result: str) -> tuple[bool, Optional[dict]]:
        is_valid, error_msg = validate_response_format(result, "pr_review")
        if not is_valid:
            logger.warning(
                "github_pr_response_format_invalid",
                error=error_msg,
                pr_number=routing.pr_number
            )

        if github_client is None:
            success = await self._post_with_curl(
                routing.owner, routing.repo, routing.pr_number, result
            )
            return success, None

        response = await github_client.post_pr_comment(
            routing.owner, routing.repo, routing.pr_number, result
        )
        logger.info("github_response_posted", type="pr", number=routing.pr_number)
        return True, response

    async def _post_to_issue(self, routing: GitHubRoutingMetadata, result: str) -> tuple[bool, Optional[dict]]:
        is_valid, error_msg = validate_response_format(result, "issue_analysis")
        if not is_valid:
            logger.warning(
                "github_issue_response_format_invalid",
                error=error_msg,
                issue_number=routing.issue_number
            )

        if github_client is None:
            success = await self._post_with_curl(
                routing.owner, routing.repo, routing.issue_number, result
            )
            return success, None

        response = await github_client.post_issue_comment(
            routing.owner, routing.repo, routing.issue_number, result
        )
        logger.info("github_response_posted", type="issue", number=routing.issue_number)
        return True, response

    async def _post_with_curl(
        self, owner: str, repo: str, number: int, body: str
    ) -> bool:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            logger.error("github_token_missing")
            return False

        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"

        try:
            proc = subprocess.run(
                [
                    "curl", "-s", "-X", "POST", url,
                    "-H", f"Authorization: Bearer {token}",
                    "-H", "Accept: application/vnd.github+json",
                    "-d", json.dumps({"body": body})
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            return proc.returncode == 0
        except Exception as e:
            logger.error("github_curl_failed", error=str(e))
            return False


class GitHubWebhookHandler:
    """Main webhook handler - coordinates the webhook processing flow."""

    def __init__(self, webhook_config):
        self.config = webhook_config
        self.response_handler = GitHubResponseHandler()

    async def verify_signature(self, request, body):
        """Verify GitHub webhook signature."""
        from api.webhooks.github.utils import verify_github_signature
        await verify_github_signature(request, body)

    def parse_payload(self, body: bytes, provider_name: str) -> dict:
        """Parse webhook payload."""
        payload = json.loads(body.decode())
        payload["provider"] = provider_name
        return payload

    async def validate_webhook(self, payload: dict):
        """Validate webhook using validation handler."""
        from api.webhooks.github.validation import validate_github_webhook
        return validate_github_webhook(payload)

    async def match_command(self, payload: dict, event_type: str):
        """Match command from webhook payload."""
        from api.webhooks.github.utils import match_github_command
        return await match_github_command(payload, event_type)

    async def send_immediate_response(self, payload: dict, command, event_type: str):
        """Send immediate response to GitHub."""
        from api.webhooks.github.utils import send_github_immediate_response
        return await send_github_immediate_response(payload, command, event_type)

    async def create_task(self, command, payload: dict, db, completion_handler: str):
        """Create task for processing."""
        from api.webhooks.github.utils import create_github_task
        return await create_github_task(command, payload, db, completion_handler)


github_response_handler = GitHubResponseHandler()
