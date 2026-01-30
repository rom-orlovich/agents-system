"""Sentry webhook handler."""

from typing import Any
import structlog

logger = structlog.get_logger()


async def handle_sentry_webhook(event_type: str, payload: dict[str, Any], queue_manager: Any) -> dict[str, str]:
    """Handle Sentry webhook event."""
    logger.info("sentry_webhook_received", event_type=event_type)

    if event_type == "issue.created":
        issue_id = payload.get("data", {}).get("issue", {}).get("id")
        task = {
            "task_id": f"sentry-{issue_id}",
            "task_type": "planning",
            "source": "sentry",
            "description": f"Fix Sentry issue {issue_id}",
            "metadata": payload,
        }
        await queue_manager.push_task("planning_tasks", task)
        logger.info("task_created_from_sentry", issue_id=issue_id)

    return {"status": "processed", "event_type": event_type}
