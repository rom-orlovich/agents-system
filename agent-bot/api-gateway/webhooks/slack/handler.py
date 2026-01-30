"""Slack webhook handler."""

from typing import Any
import structlog

logger = structlog.get_logger()


async def handle_slack_webhook(event_type: str, payload: dict[str, Any], queue_manager: Any) -> dict[str, str]:
    """Handle Slack webhook event."""
    logger.info("slack_webhook_received", event_type=event_type)

    if event_type == "message":
        text = payload.get("event", {}).get("text", "")

        if text.startswith("/agent"):
            command = text.replace("/agent", "").strip()
            task = {
                "task_id": f"slack-{payload.get('event_id')}",
                "task_type": "execution",
                "source": "slack",
                "description": command,
                "metadata": payload,
            }
            await queue_manager.push_task("planning_tasks", task)
            logger.info("task_created_from_slack", command=command)

    return {"status": "processed", "event_type": event_type}
