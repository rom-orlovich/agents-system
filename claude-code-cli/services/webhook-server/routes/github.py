"""GitHub webhook routes."""

import sys
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from config import settings
from models import TaskStatus
from task_queue import RedisQueue
from github_client import validate_webhook_signature

router = APIRouter()
queue = RedisQueue()


async def verify_github_signature(request: Request) -> bytes:
    """Verify GitHub webhook signature and return payload.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Raw payload bytes
        
    Raises:
        HTTPException: If signature is invalid
    """
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    if not validate_webhook_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    return payload


@router.post("/")
async def github_webhook(request: Request):
    """Handle GitHub webhook events."""
    # Validate webhook signature for security
    await verify_github_signature(request)
    
    payload = await request.json()

    # Handle PR comments for approval
    if "comment" in payload and "issue" in payload:
        comment_body = payload["comment"].get("body", "").lower()
        pr_number = payload["issue"].get("number")
        repo_full_name = payload.get("repository", {}).get("full_name", "")

        # Check for approval command
        if "@agent approve" in comment_body:
            # Extract task_id from PR (placeholder logic)
            task_id = f"task-{pr_number}"  # Simplified

            # Move to execution queue
            task_data = await queue.get_task(task_id)
            if task_data:
                await queue.update_task_status(task_id, TaskStatus.APPROVED)
                await queue.push(settings.EXECUTION_QUEUE, task_data)

                print(f"✅ Task {task_id} approved via GitHub ({repo_full_name}#{pr_number})")

                return {"status": "approved", "task_id": task_id}

    return {"status": "processed"}


@router.get("/test")
async def test_github_webhook():
    """Test endpoint."""
    return {"status": "GitHub webhook endpoint is working"}
