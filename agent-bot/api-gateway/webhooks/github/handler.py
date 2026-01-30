"""GitHub webhook handler."""

import hashlib
import hmac
from typing import Any
from fastapi import HTTPException
import structlog

logger = structlog.get_logger()


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    expected_signature = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


async def handle_github_webhook(event_type: str, payload: dict[str, Any], queue_manager: Any) -> dict[str, str]:
    """Handle GitHub webhook event."""
    logger.info("github_webhook_received", event_type=event_type)

    if event_type == "pull_request":
        action = payload.get("action")
        pr_number = payload.get("pull_request", {}).get("number")

        if action == "opened" or action == "synchronize":
            task = {
                "task_id": f"pr-{pr_number}",
                "task_type": "verification",
                "source": "github",
                "description": f"Review PR #{pr_number}",
                "metadata": payload,
            }
            await queue_manager.push_task("planning_tasks", task)
            logger.info("task_created_from_pr", pr_number=pr_number)

    elif event_type == "issues":
        action = payload.get("action")
        if action == "labeled":
            labels = payload.get("issue", {}).get("labels", [])
            if any(label.get("name") == "AI-Fix" for label in labels):
                issue_number = payload.get("issue", {}).get("number")
                task = {
                    "task_id": f"issue-{issue_number}",
                    "task_type": "planning",
                    "source": "github",
                    "description": payload.get("issue", {}).get("body", ""),
                    "metadata": payload,
                }
                await queue_manager.push_task("planning_tasks", task)
                logger.info("task_created_from_issue", issue_number=issue_number)

    return {"status": "processed", "event_type": event_type}
