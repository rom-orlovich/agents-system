"""GitHub webhook routes.

Handles GitHub webhooks including:
- PR comments with bot commands (@agent approve, @agent help, etc.)
- PR review events
- Issue events
"""

import sys
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.config import settings
from shared.models import TaskStatus
from shared.task_queue import RedisQueue
from shared.github_client import validate_webhook_signature
from shared.commands import CommandParser
from shared.commands.executor import CommandExecutor
from shared.enums import Platform
from shared.constants import BOT_CONFIG

router = APIRouter()
queue = RedisQueue()
command_parser = CommandParser()
command_executor = CommandExecutor(redis=queue)

logger = logging.getLogger("github-webhook")


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


def extract_task_id_from_pr(pr_number: int, repository: str) -> str:
    """Extract task ID from PR.
    
    In production, this would look up the task from the PR URL or body.
    For now, we use a simple format.
    
    Args:
        pr_number: PR number
        repository: Repository full name
        
    Returns:
        Task ID string
    """
    # TODO: Look up actual task from database/redis by PR URL
    return f"task-{pr_number}"


@router.post("/")
async def github_webhook(request: Request):
    """Handle GitHub webhook events.
    
    Processes:
    - issue_comment: Bot commands in PR comments
    - pull_request_review: Review approvals
    - push: CI status updates
    """
    # Validate webhook signature for security
    await verify_github_signature(request)
    
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    
    logger.info(f"GitHub webhook received: {event_type}")
    
    # Handle PR comments for bot commands
    if "comment" in payload and "issue" in payload:
        return await handle_pr_comment(payload)
    
    # Handle PR review events
    if event_type == "pull_request_review":
        return await handle_pr_review(payload)
    
    # Handle push events (for CI status)
    if event_type == "push":
        return await handle_push(payload)
    
    return {"status": "processed", "event": event_type}


async def handle_pr_comment(payload: dict):
    """Handle PR comment events - parse and execute bot commands.
    
    Args:
        payload: GitHub webhook payload
        
    Returns:
        Response dict
    """
    comment_body = payload["comment"].get("body", "")
    pr_number = payload["issue"].get("number")
    repo_full_name = payload.get("repository", {}).get("full_name", "")
    comment_author = payload["comment"].get("user", {}).get("login", "")
    comment_id = payload["comment"].get("id")
    pr_url = payload["issue"].get("html_url", "")
    
    logger.info(
        f"PR comment from @{comment_author}: {comment_body[:100]}..."
    )
    
    # Check if this mentions the bot
    mentions_bot = any(
        tag.lower() in comment_body.lower() 
        for tag in BOT_CONFIG.tags
    )
    
    if not mentions_bot:
        logger.debug("Comment doesn't mention bot, ignoring")
        return {"status": "ignored", "reason": "no bot mention"}
    
    # Extract task ID from PR
    task_id = extract_task_id_from_pr(pr_number, repo_full_name)
    
    # Build context for command parser
    context = {
        "pr_number": pr_number,
        "repository": repo_full_name,
        "comment_id": comment_id,
        "author": comment_author,
        "pr_url": pr_url,
        "task_id": task_id,
    }
    
    # Parse the command
    parsed = command_parser.parse(
        text=comment_body,
        platform=Platform.GITHUB,
        context=context
    )
    
    if not parsed:
        logger.warning(f"Could not parse command from: {comment_body[:50]}")
        return {"status": "error", "reason": "invalid command"}
    
    logger.info(
        f"Parsed command: {parsed.command_name}",
        command_type=parsed.command_type.value,
        args=parsed.args
    )
    
    # Execute the command
    result = await command_executor.execute(parsed)
    
    logger.info(
        f"Command executed: {parsed.command_name}",
        success=result.success,
        should_reply=result.should_reply
    )
    
    # TODO: Post result as PR comment if result.should_reply
    # This would use GitHub API to post a comment:
    # if result.should_reply:
    #     await github_client.post_comment(
    #         owner=repo_full_name.split("/")[0],
    #         repo=repo_full_name.split("/")[1],
    #         issue_number=pr_number,
    #         body=result.message
    #     )
    
    return {
        "status": "executed",
        "command": parsed.command_name,
        "success": result.success,
        "task_id": task_id
    }


async def handle_pr_review(payload: dict):
    """Handle PR review events.
    
    If review state is "approved" from an authorized user,
    treat it as an approval command.
    
    Args:
        payload: GitHub webhook payload
        
    Returns:
        Response dict
    """
    review = payload.get("review", {})
    state = review.get("state", "").lower()
    reviewer = review.get("user", {}).get("login", "")
    pr_number = payload.get("pull_request", {}).get("number")
    repo_full_name = payload.get("repository", {}).get("full_name", "")
    
    logger.info(f"PR review from @{reviewer}: {state}")
    
    if state == "approved":
        task_id = extract_task_id_from_pr(pr_number, repo_full_name)
        task_data = await queue.get_task(task_id)
        
        if task_data:
            await queue.update_task_status(task_id, TaskStatus.APPROVED)
            await queue.push(settings.EXECUTION_QUEUE, task_data)
            
            logger.info(f"Task {task_id} approved via PR review")
            
            return {
                "status": "approved",
                "task_id": task_id,
                "approved_by": reviewer
            }
    
    return {"status": "processed", "review_state": state}


async def handle_push(payload: dict):
    """Handle push events - for CI status updates.
    
    Args:
        payload: GitHub webhook payload
        
    Returns:
        Response dict
    """
    ref = payload.get("ref", "")
    repo_full_name = payload.get("repository", {}).get("full_name", "")
    
    logger.info(f"Push to {repo_full_name}: {ref}")
    
    # Could trigger CI status checks here
    return {"status": "processed", "ref": ref}


@router.get("/test")
async def test_github_webhook():
    """Test endpoint."""
    return {
        "status": "GitHub webhook endpoint is working",
        "bot_tags": BOT_CONFIG.tags,
        "bot_name": BOT_CONFIG.name
    }
