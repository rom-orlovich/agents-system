"""
Sentry webhook handler plugin.
"""

import os
import logging
from typing import Dict, Any, Optional

from core.webhook_base import BaseWebhookHandler, WebhookMetadata, WebhookResponse

# Import shared modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from config import settings
from models import TaskSource
from task_queue import RedisQueue

logger = logging.getLogger(__name__)


class SentryWebhookHandler(BaseWebhookHandler):
    """
    Handler for Sentry webhook events.

    Processes:
    1. New error events → Queue for planning
    2. Issue alerts → Queue for analysis
    """

    def __init__(self):
        self.queue = RedisQueue()

    @property
    def metadata(self) -> WebhookMetadata:
        return WebhookMetadata(
            name="sentry",
            endpoint="/webhooks/sentry",
            description="Handle Sentry error events and issue alerts",
            secret_env_var="SENTRY_WEBHOOK_SECRET",
            enabled=True
        )

    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate Sentry webhook signature.

        For now, we trust Sentry webhooks. In production, you should
        configure webhook authentication in Sentry settings.
        """
        # TODO: Implement Sentry signature validation if configured
        return True

    async def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse Sentry webhook payload.

        Extracts:
        - event_data: Error event data
        - sentry_issue_id: Sentry issue ID
        - title: Issue title/message
        - tags: Event tags (including custom repository tag)
        - repository: Repository name from tags
        """
        try:
            # Sentry Issue Alert payload: payload["data"]["event"]
            event_data = payload.get("data", {}).get("event", {})

            # Extract tags
            tags = self._extract_tags(event_data)

            # Extract repository from custom tag
            repository = tags.get("repository", "unknown/repo")

            # Extract error message
            message = event_data.get("message") or payload.get("title") or "Sentry error"

            return {
                "event_data": event_data,
                "sentry_issue_id": payload.get("id"),
                "title": message,
                "tags": tags,
                "repository": repository,
            }

        except Exception as e:
            logger.error(f"Failed to parse Sentry webhook payload: {e}")
            return None

    async def should_process(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Determine if this Sentry event should be processed.

        Process all Sentry events (they're already filtered at Sentry side).
        """
        # Process all events - filtering happens in Sentry alert rules
        return True

    async def handle(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """
        Process the Sentry webhook.

        Queues error for analysis and planning.
        """
        sentry_issue_id = parsed_data.get("sentry_issue_id")
        repository = parsed_data.get("repository", "unknown/repo")
        title = parsed_data.get("title", "Sentry error")

        logger.info(
            f"Processing Sentry webhook: {sentry_issue_id} for {repository}"
        )

        # Create task data
        task_data = {
            "source": TaskSource.SENTRY.value,
            "description": title,
            "sentry_issue_id": sentry_issue_id,
            "repository": repository
        }

        # Queue for planning
        task_id = await self.queue.push(settings.PLANNING_QUEUE, task_data)

        logger.info(
            f"Sentry error queued: {task_id} "
            f"(Issue: {sentry_issue_id}, Repo: {repository})"
        )

        return WebhookResponse(
            status="queued",
            task_id=task_id,
            message=f"Sentry error {sentry_issue_id} queued for planning",
            details={
                "sentry_issue_id": sentry_issue_id,
                "repository": repository,
                "queue": settings.PLANNING_QUEUE
            }
        )

    @staticmethod
    def _extract_tags(event_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract tags from Sentry event data.

        Sentry tags can be:
        - List of lists: [['key', 'value'], ...]
        - List of dicts: [{'key': 'k', 'value': 'v'}, ...]

        Args:
            event_data: Sentry event data

        Returns:
            Dict of tag key-value pairs
        """
        tags = event_data.get("tags", [])

        if not isinstance(tags, list):
            return tags if isinstance(tags, dict) else {}

        result = {}
        for tag in tags:
            if isinstance(tag, list) and len(tag) >= 2:
                # Format: ['key', 'value']
                result[tag[0]] = tag[1]
            elif isinstance(tag, dict) and "key" in tag and "value" in tag:
                # Format: {'key': 'k', 'value': 'v'}
                result[tag["key"]] = tag["value"]

        return result
