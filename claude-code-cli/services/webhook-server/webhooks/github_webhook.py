"""
GitHub webhook handler plugin.
"""

import os
import logging
from typing import Dict, Any, Optional

from core.webhook_base import BaseWebhookHandler, WebhookMetadata, WebhookResponse
from core.webhook_validator import WebhookValidator

# Import shared modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from config import settings
from models import TaskSource, TaskStatus
from task_queue import RedisQueue

logger = logging.getLogger(__name__)


class GitHubWebhookHandler(BaseWebhookHandler):
    """
    Handler for GitHub webhook events.

    Processes:
    1. PR comment events with "@agent approve" → Queue for execution
    2. PR review events → Handle approval/rejection
    """

    def __init__(self):
        self.queue = RedisQueue()

    @property
    def metadata(self) -> WebhookMetadata:
        return WebhookMetadata(
            name="github",
            endpoint="/webhooks/github",
            description="Handle GitHub PR comments and reviews",
            secret_env_var="GITHUB_WEBHOOK_SECRET",
            enabled=True
        )

    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate GitHub webhook signature (X-Hub-Signature-256).

        Args:
            payload: Raw webhook payload bytes
            signature: Signature from X-Hub-Signature-256 header

        Returns:
            True if signature is valid, False otherwise
        """
        secret = os.getenv(self.metadata.secret_env_var)
        if not secret:
            logger.warning("GitHub webhook secret not configured")
            return True  # Allow in development

        # GitHub uses sha256= prefix
        return WebhookValidator.validate_hmac_sha256(
            payload=payload,
            signature=signature,
            secret=secret,
            signature_prefix="sha256="
        )

    async def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse GitHub webhook payload.

        Extracts:
        - event_type: Type of event (comment, review, etc.)
        - pr_number: PR number
        - repository: Full repository name (owner/repo)
        - comment_body: Comment text (if comment event)
        - action: Event action (created, edited, etc.)
        """
        try:
            repository = payload.get("repository", {}).get("full_name", "")

            # Parse comment events
            if "comment" in payload and "issue" in payload:
                return {
                    "event_type": "comment",
                    "pr_number": payload["issue"].get("number"),
                    "repository": repository,
                    "comment_body": payload["comment"].get("body", ""),
                    "action": payload.get("action", ""),
                    "comment_url": payload["comment"].get("html_url", ""),
                }

            # Parse PR review events
            if "review" in payload and "pull_request" in payload:
                return {
                    "event_type": "review",
                    "pr_number": payload["pull_request"].get("number"),
                    "repository": repository,
                    "review_state": payload["review"].get("state", ""),
                    "review_body": payload["review"].get("body", ""),
                    "action": payload.get("action", ""),
                }

            # Unknown event type
            return None

        except Exception as e:
            logger.error(f"Failed to parse GitHub webhook payload: {e}")
            return None

    async def should_process(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Determine if this GitHub event should be processed.

        Process if:
        1. Comment contains "@agent approve" → Approve and execute
        2. PR review is "approved" → Approve and execute
        """
        event_type = parsed_data.get("event_type", "")

        # Comment with approval command
        if event_type == "comment":
            comment_body = parsed_data.get("comment_body", "").lower()
            return "@agent approve" in comment_body

        # PR review approval
        if event_type == "review":
            review_state = parsed_data.get("review_state", "").lower()
            return review_state == "approved"

        return False

    async def handle(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """
        Process the GitHub webhook.

        Handles approval via comment or review.
        """
        event_type = parsed_data.get("event_type", "")
        pr_number = parsed_data.get("pr_number")
        repository = parsed_data.get("repository", "")

        logger.info(
            f"Processing GitHub webhook: {event_type} for PR #{pr_number} "
            f"in {repository}"
        )

        # Extract task_id from PR
        # In real implementation, we'd fetch PR description/labels to get task_id
        # For now, using simplified logic
        task_id = f"task-{pr_number}"  # Simplified

        # Get task data
        task_data = await self.queue.get_task(task_id)

        if not task_data:
            logger.warning(f"Task {task_id} not found for PR #{pr_number}")
            return WebhookResponse(
                status="ignored",
                message=f"No task found for PR #{pr_number}",
                details={
                    "pr_number": pr_number,
                    "repository": repository
                }
            )

        # Approve task and queue for execution
        await self.queue.update_task_status(task_id, TaskStatus.APPROVED)
        new_task_id = await self.queue.push(settings.EXECUTION_QUEUE, task_data)

        logger.info(
            f"Task {task_id} approved via GitHub "
            f"({repository}#{pr_number}), queued for execution: {new_task_id}"
        )

        return WebhookResponse(
            status="queued",
            task_id=new_task_id,
            message=f"Task approved via GitHub PR #{pr_number} and queued for execution",
            details={
                "pr_number": pr_number,
                "repository": repository,
                "event_type": event_type,
                "queue": settings.EXECUTION_QUEUE
            }
        )
