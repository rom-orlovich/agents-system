"""GitHub webhook routes."""

import sys
from pathlib import Path
from fastapi import APIRouter, Request

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from config import settings
from models import TaskStatus
from task_queue import RedisQueue

router = APIRouter()
queue = RedisQueue()


@router.post("/")
async def github_webhook(request: Request):
    """Handle GitHub webhook events."""
    payload = await request.json()

    # Handle PR comments for approval
    if "comment" in payload and "issue" in payload:
        comment_body = payload["comment"].get("body", "").lower()
        pr_number = payload["issue"].get("number")

        # Check for approval command
        if "@agent approve" in comment_body:
            # Extract task_id from PR (placeholder logic)
            task_id = f"task-{pr_number}"  # Simplified

            # Move to execution queue
            task_data = await queue.get_task(task_id)
            if task_data:
                await queue.update_task_status(task_id, TaskStatus.APPROVED)
                await queue.push(settings.EXECUTION_QUEUE, task_data)

                print(f"✅ Task {task_id} approved via GitHub")

                return {"status": "approved", "task_id": task_id}

    return {"status": "processed"}


@router.get("/test")
async def test_github_webhook():
    """Test endpoint."""
    return {"status": "GitHub webhook endpoint is working"}
