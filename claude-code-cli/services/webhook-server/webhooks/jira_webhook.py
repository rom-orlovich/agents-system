"""
Jira webhook handler plugin.
"""

import os
import re
import logging
from typing import Dict, Any, Optional

from core.webhook_base import BaseWebhookHandler, WebhookMetadata, WebhookResponse
from core.webhook_validator import WebhookValidator

# Import shared modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from config import settings
from models import TaskSource
from task_queue import RedisQueue

logger = logging.getLogger(__name__)


class JiraWebhookHandler(BaseWebhookHandler):
    """
    Handler for Jira webhook events.

    Processes:
    1. Sentry-created tickets (auto-enrichment)
    2. Tickets with AI-Fix label (manual requests)
    3. Ticket transitions to "Approved" status (approval flow)
    """

    def __init__(self):
        self.queue = RedisQueue()

    @property
    def metadata(self) -> WebhookMetadata:
        return WebhookMetadata(
            name="jira",
            endpoint="/webhooks/jira",
            description="Handle Jira issue events (created, updated, transitions)",
            secret_env_var="JIRA_WEBHOOK_SECRET",
            enabled=True
        )

    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate Jira webhook signature.

        For now, we trust Jira webhooks. In production, you should
        configure webhook authentication in Jira settings.
        """
        # TODO: Implement Jira signature validation if configured
        # For now, return True as Jira typically uses IP allowlisting
        return True

    async def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse Jira webhook payload.

        Extracts:
        - webhook_event: Type of event (created, updated, etc.)
        - issue_key: Jira issue key (e.g., "PROJ-123")
        - summary: Issue summary/title
        - description: Issue description
        - labels: Issue labels
        - status: Current issue status
        - sentry_issue_id: Sentry issue ID if found
        - repository: Repository name if found
        """
        try:
            webhook_event = payload.get("webhookEvent", "")
            issue = payload.get("issue", {})
            issue_key = issue.get("key", "")
            fields = issue.get("fields", {})

            # Get description (might be in Atlassian Document Format)
            description = fields.get("description", "")
            if isinstance(description, dict):
                # Atlassian Document Format (ADF)
                description = str(description.get("content", ""))

            summary = fields.get("summary", "")
            labels = fields.get("labels", [])
            status = fields.get("status", {}).get("name", "")

            # Extract Sentry issue ID if present
            sentry_issue_id = self._extract_sentry_issue_id(description)

            # Extract repository if present
            repository = self._extract_repository(description)

            # Get changelog for transition events
            changelog = payload.get("changelog", {})

            return {
                "webhook_event": webhook_event,
                "issue_key": issue_key,
                "summary": summary,
                "description": description,
                "labels": labels,
                "status": status,
                "sentry_issue_id": sentry_issue_id,
                "repository": repository,
                "changelog": changelog,
            }

        except Exception as e:
            logger.error(f"Failed to parse Jira webhook payload: {e}")
            return None

    async def should_process(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Determine if this Jira event should be processed.

        Process if:
        1. New ticket created with Sentry issue → enrich
        2. New ticket created with AI-Fix label → plan
        3. Ticket transitioned to "Approved" status → execute
        """
        webhook_event = parsed_data.get("webhook_event", "")
        labels = parsed_data.get("labels", [])
        status = parsed_data.get("status", "")
        sentry_issue_id = parsed_data.get("sentry_issue_id")
        summary = parsed_data.get("summary", "")
        changelog = parsed_data.get("changelog", {})

        # CASE 1: Ticket created with Sentry issue
        if webhook_event == "jira:issue_created":
            is_sentry_ticket = sentry_issue_id is not None or "sentry" in summary.lower()
            if is_sentry_ticket:
                return True

            # CASE 2: Ticket created with AI-Fix label
            if "AI-Fix" in labels:
                return True

        # CASE 3: Ticket transitioned to Approved
        if webhook_event == "jira:issue_updated":
            items = changelog.get("items", [])
            for item in items:
                if item.get("field") == "status":
                    new_status = item.get("toString", "").lower()
                    if new_status in ["approved", "in progress"]:
                        return True

        return False

    async def handle(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """
        Process the Jira webhook.

        Routes to appropriate handler based on event type.
        """
        webhook_event = parsed_data.get("webhook_event", "")
        issue_key = parsed_data.get("issue_key", "")
        summary = parsed_data.get("summary", "")
        status = parsed_data.get("status", "")
        labels = parsed_data.get("labels", [])
        sentry_issue_id = parsed_data.get("sentry_issue_id")

        logger.info(
            f"Processing Jira webhook: {webhook_event} for {issue_key} "
            f"(status={status}, labels={labels})"
        )

        # CASE 1: Approval transition
        if webhook_event == "jira:issue_updated":
            changelog = parsed_data.get("changelog", {})
            items = changelog.get("items", [])

            for item in items:
                if item.get("field") == "status":
                    new_status = item.get("toString", "").lower()
                    if new_status in ["approved", "in progress"]:
                        return await self._handle_approval(parsed_data)

        # CASE 2: Sentry-created ticket
        if webhook_event == "jira:issue_created" and sentry_issue_id:
            return await self._handle_sentry_ticket(parsed_data)

        # CASE 3: Manual AI-Fix request
        if webhook_event == "jira:issue_created" and "AI-Fix" in labels:
            return await self._handle_manual_fix(parsed_data)

        # Should not reach here if should_process() is correct
        return WebhookResponse(
            status="ignored",
            message=f"No handler for event: {webhook_event}",
            details={"issue_key": issue_key}
        )

    async def _handle_approval(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """Handle ticket approval - queue for execution."""
        issue_key = parsed_data.get("issue_key", "")
        sentry_issue_id = parsed_data.get("sentry_issue_id")
        repository = parsed_data.get("repository")

        logger.info(f"Ticket {issue_key} approved via Jira status transition")

        task_data = {
            "source": TaskSource.JIRA.value,
            "action": "approve",
            "issue_key": issue_key,
            "sentry_issue_id": sentry_issue_id,
            "repository": repository
        }

        task_id = await self.queue.push(settings.EXECUTION_QUEUE, task_data)

        return WebhookResponse(
            status="queued",
            task_id=task_id,
            message=f"Ticket {issue_key} approved and queued for execution",
            details={
                "issue_key": issue_key,
                "queue": settings.EXECUTION_QUEUE
            }
        )

    async def _handle_sentry_ticket(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """Handle Sentry-created ticket - queue for enrichment."""
        issue_key = parsed_data.get("issue_key", "")
        sentry_issue_id = parsed_data.get("sentry_issue_id")
        summary = parsed_data.get("summary", "")
        description = parsed_data.get("description", "")
        repository = parsed_data.get("repository")

        logger.info(f"Detected Sentry-created ticket: {sentry_issue_id}")

        task_data = {
            "source": TaskSource.JIRA.value,
            "action": "enrich",
            "description": summary,
            "issue_key": issue_key,
            "sentry_issue_id": sentry_issue_id,
            "repository": repository,
            "full_description": description[:2000]  # Limit size
        }

        task_id = await self.queue.push(settings.PLANNING_QUEUE, task_data)

        logger.info(
            f"Sentry ticket enrichment queued: {task_id} "
            f"(Issue: {issue_key}, Sentry: {sentry_issue_id})"
        )

        return WebhookResponse(
            status="queued",
            task_id=task_id,
            message=f"Sentry ticket {issue_key} queued for enrichment",
            details={
                "issue_key": issue_key,
                "sentry_issue_id": sentry_issue_id,
                "queue": settings.PLANNING_QUEUE
            }
        )

    async def _handle_manual_fix(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """Handle manual AI-Fix request - queue for planning."""
        issue_key = parsed_data.get("issue_key", "")
        summary = parsed_data.get("summary", "")
        repository = parsed_data.get("repository")

        logger.info(f"Manual AI-Fix request: {issue_key}")

        task_data = {
            "source": TaskSource.JIRA.value,
            "action": "fix",
            "description": summary,
            "issue_key": issue_key,
            "repository": repository
        }

        task_id = await self.queue.push(settings.PLANNING_QUEUE, task_data)

        logger.info(f"Manual AI-Fix queued: {task_id} (Issue: {issue_key})")

        return WebhookResponse(
            status="queued",
            task_id=task_id,
            message=f"AI-Fix request {issue_key} queued for planning",
            details={
                "issue_key": issue_key,
                "queue": settings.PLANNING_QUEUE
            }
        )

    @staticmethod
    def _extract_sentry_issue_id(description: str) -> Optional[str]:
        """
        Extract Sentry issue ID from Jira ticket description.

        Sentry creates tickets with patterns like:
        - "Sentry Issue: [JAVASCRIPT-REACT-1](https://sentry.io/...)"
        - "Sentry Issue: JAVASCRIPT-REACT-1"
        - Just "JAVASCRIPT-REACT-1" somewhere in text
        """
        if not description:
            return None

        # Pattern 1: Markdown link format [ISSUE-ID](url)
        pattern1 = r"Sentry Issue:\s*\[([A-Z]+-[A-Z]+-\d+)\]"
        match = re.search(pattern1, description, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern 2: Plain text format "Sentry Issue: ISSUE-ID"
        pattern2 = r"Sentry Issue:\s*([A-Z]+-[A-Z]+-\d+)"
        match = re.search(pattern2, description, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern 3: Just look for the issue ID pattern anywhere
        pattern3 = r"([A-Z]+-[A-Z]+-\d+)"
        match = re.search(pattern3, description)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def _extract_repository(description: str) -> Optional[str]:
        """
        Extract repository name from Jira ticket description.

        Looks for patterns like:
        - "Repository: owner/repo"
        - "github.com/owner/repo"
        """
        if not description:
            return None

        # Pattern 1: GitHub URL
        pattern1 = r"github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)"
        match = re.search(pattern1, description)
        if match:
            return match.group(1)

        # Pattern 2: Repository: owner/repo
        pattern2 = r"[Rr]epository:\s*([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)"
        match = re.search(pattern2, description)
        if match:
            return match.group(1)

        return None
