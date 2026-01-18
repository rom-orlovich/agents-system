"""Slack webhook routes."""

import sys
from pathlib import Path
from fastapi import APIRouter, Request

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from config import settings
from models import TaskSource, TaskStatus
from queue import RedisQueue

router = APIRouter()
queue = RedisQueue()


@router.post("/")
async def slack_webhook(request: Request):
    """Handle Slack webhook events."""
    payload = await request.json()

    # Handle different Slack event types
    if payload.get("type") == "url_verification":
        # Slack URL verification
        return {"challenge": payload.get("challenge")}

    # Handle button clicks (approvals)
    if "actions" in payload:
        action = payload["actions"][0]
        action_id = action.get("action_id")
        task_id = action.get("value")

        if action_id == "approve_task":
            # Approve task
            task_data = await queue.get_task(task_id)
            if task_data:
                await queue.update_task_status(task_id, TaskStatus.APPROVED)
                await queue.push(settings.EXECUTION_QUEUE, task_data)

                print(f"✅ Task {task_id} approved via Slack")

                return {"status": "approved"}

        elif action_id == "reject_task":
            # Reject task
            await queue.update_task_status(task_id, TaskStatus.REJECTED)

            print(f"❌ Task {task_id} rejected via Slack")

            return {"status": "rejected"}

    return {"status": "processed"}


@router.get("/test")
async def test_slack_webhook():
    """Test endpoint."""
    return {"status": "Slack webhook endpoint is working"}
