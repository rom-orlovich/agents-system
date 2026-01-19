"""Sentry webhook routes."""

import sys
from pathlib import Path
from fastapi import APIRouter, Request

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from config import settings
from models import TaskSource
from task_queue import RedisQueue

router = APIRouter()
queue = RedisQueue()


@router.post("/")
async def sentry_webhook(request: Request):
    """Handle Sentry webhook events."""
    payload = await request.json()

    # Extract Sentry issue data
    task_data = {
        "source": TaskSource.SENTRY.value,
        "description": payload.get("title", "Sentry error"),
        "sentry_issue_id": payload.get("id"),
        "repository": None
    }

    # Add to planning queue
    task_id = await queue.push(settings.PLANNING_QUEUE, task_data)

    print(f"📥 Sentry task queued: {task_id}")

    return {"status": "queued", "task_id": task_id}


@router.get("/test")
async def test_sentry_webhook():
    """Test endpoint."""
    return {"status": "Sentry webhook endpoint is working"}
