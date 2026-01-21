"""
Slack webhook handler plugin.
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
from models import TaskSource, TaskStatus
from task_queue import RedisQueue

logger = logging.getLogger(__name__)


class SlackWebhookHandler(BaseWebhookHandler):
    """
    Handler for Slack webhook events.

    Processes:
    1. URL verification (initial setup)
    2. Button clicks for task approval/rejection
    3. Slash commands (future)
    """

    def __init__(self):
        self.queue = RedisQueue()

    @property
    def metadata(self) -> WebhookMetadata:
        return WebhookMetadata(
            name="slack",
            endpoint="/webhooks/slack",
            description="Handle Slack interactive components and slash commands",
            secret_env_var="SLACK_WEBHOOK_SECRET",
            enabled=True
        )

    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate Slack webhook signature.

        Slack uses X-Slack-Signature header with HMAC-SHA256.
        """
        # TODO: Implement Slack signature validation
        # For now, trust Slack webhooks
        return True

    async def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse Slack webhook payload.

        Extracts:
        - event_type: Type of event (url_verification, block_actions, etc.)
        - challenge: Challenge string (for URL verification)
        - actions: Button click actions
        - action_id: ID of clicked button
        - task_id: Task ID from button value
        """
        try:
            event_type = payload.get("type", "")

            # URL verification event
            if event_type == "url_verification":
                return {
                    "event_type": "url_verification",
                    "challenge": payload.get("challenge", "")
                }

            # Interactive component (button click)
            if "actions" in payload:
                action = payload["actions"][0] if payload["actions"] else {}
                return {
                    "event_type": "block_actions",
                    "action_id": action.get("action_id", ""),
                    "task_id": action.get("value", ""),
                    "user_id": payload.get("user", {}).get("id", ""),
                    "user_name": payload.get("user", {}).get("name", ""),
                }

            # Slash command (future)
            if "command" in payload:
                return {
                    "event_type": "slash_command",
                    "command": payload.get("command", ""),
                    "text": payload.get("text", ""),
                    "user_id": payload.get("user_id", ""),
                    "user_name": payload.get("user_name", ""),
                }

            return None

        except Exception as e:
            logger.error(f"Failed to parse Slack webhook payload: {e}")
            return None

    async def should_process(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Determine if this Slack event should be processed.

        Process:
        1. URL verification (always)
        2. Approval/rejection button clicks
        """
        event_type = parsed_data.get("event_type", "")

        # Always process URL verification
        if event_type == "url_verification":
            return True

        # Process button actions
        if event_type == "block_actions":
            action_id = parsed_data.get("action_id", "")
            return action_id in ["approve_task", "reject_task"]

        return False

    async def handle(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """
        Process the Slack webhook.

        Handles:
        1. URL verification → Return challenge
        2. Task approval → Move to execution queue
        3. Task rejection → Update status
        """
        event_type = parsed_data.get("event_type", "")

        # URL verification
        if event_type == "url_verification":
            challenge = parsed_data.get("challenge", "")
            logger.info("Handling Slack URL verification")
            return WebhookResponse(
                status="verified",
                message="URL verification successful",
                details={"challenge": challenge}
            )

        # Button actions
        if event_type == "block_actions":
            return await self._handle_button_action(parsed_data)

        return WebhookResponse(
            status="ignored",
            message=f"No handler for event type: {event_type}"
        )

    async def _handle_button_action(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """
        Handle Slack button click action.

        Args:
            parsed_data: Parsed event data

        Returns:
            WebhookResponse with action result
        """
        action_id = parsed_data.get("action_id", "")
        task_id = parsed_data.get("task_id", "")
        user_name = parsed_data.get("user_name", "unknown")

        logger.info(
            f"Handling Slack button action: {action_id} for task {task_id} "
            f"by user {user_name}"
        )

        # Approve task
        if action_id == "approve_task":
            task_data = await self.queue.get_task(task_id)
            if not task_data:
                return WebhookResponse(
                    status="error",
                    message=f"Task {task_id} not found",
                    details={"task_id": task_id}
                )

            # Update status and queue for execution
            await self.queue.update_task_status(
                task_id,
                TaskStatus.APPROVED,
                approved_by=user_name
            )
            new_task_id = await self.queue.push(settings.EXECUTION_QUEUE, task_data)

            logger.info(
                f"Task {task_id} approved by {user_name} via Slack, "
                f"queued for execution: {new_task_id}"
            )

            return WebhookResponse(
                status="approved",
                task_id=new_task_id,
                message=f"Task {task_id} approved by {user_name} and queued for execution",
                details={
                    "approved_by": user_name,
                    "queue": settings.EXECUTION_QUEUE
                }
            )

        # Reject task
        elif action_id == "reject_task":
            await self.queue.update_task_status(
                task_id,
                TaskStatus.REJECTED,
                approved_by=user_name
            )

            logger.info(f"Task {task_id} rejected by {user_name} via Slack")

            return WebhookResponse(
                status="rejected",
                message=f"Task {task_id} rejected by {user_name}",
                details={"rejected_by": user_name}
            )

        return WebhookResponse(
            status="ignored",
            message=f"Unknown action: {action_id}"
        )
