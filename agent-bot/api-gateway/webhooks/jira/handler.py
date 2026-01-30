"""Jira webhook handler."""

from typing import Any
import structlog

logger = structlog.get_logger()


async def handle_jira_webhook(event_type: str, payload: dict[str, Any], queue_manager: Any) -> dict[str, str]:
    """Handle Jira webhook event."""
    logger.info("jira_webhook_received", event_type=event_type)

    if event_type == "jira:issue_updated":
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        labels = fields.get("labels", [])

        if "AI-Fix" in labels:
            issue_key = issue.get("key")
            task = {
                "task_id": f"jira-{issue_key}",
                "task_type": "planning",
                "source": "jira",
                "description": fields.get("description", ""),
                "metadata": payload,
            }
            await queue_manager.push_task("planning_tasks", task)
            logger.info("task_created_from_jira", issue_key=issue_key)

    return {"status": "processed", "event_type": event_type}
