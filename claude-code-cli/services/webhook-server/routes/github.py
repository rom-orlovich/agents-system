"""GitHub webhook routes.

Handles GitHub webhooks including:
- PR comments with bot commands (@agent approve, @agent help, etc.)
- PR review events
- Issue events
"""

import json
import sys
import urllib.parse
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.config import settings
from shared.models import TaskStatus, GitHubTask
from shared.task_queue import RedisQueue
from shared.github_client import validate_webhook_signature, GitHubClient
from shared.commands import CommandParser
from shared.commands.executor import CommandExecutor
from shared.enums import Platform
from shared.constants import BOT_CONFIG

router = APIRouter()
queue = RedisQueue()
command_parser = CommandParser()
github_client = GitHubClient()
command_executor = CommandExecutor(redis=queue, github=github_client)


logger = logging.getLogger("github-webhook")
# Use the root logger's configuration if already set up
if not logger.handlers and not logging.getLogger().handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)


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


async def get_task_id_for_pr(pr_number: int, repository: str) -> str:
    """Look up task ID from PR using Redis.
    
    First tries to find an existing task linked to this PR.
    Falls back to a generated ID if no task is found.
    
    Args:
        pr_number: PR number
        repository: Repository full name
        
    Returns:
        Task ID string
    """
    # Try to find existing task by PR
    task_id = await queue.get_task_id_by_pr(pr_number, repository)
    
    if task_id:
        logger.info(f"Found existing task {task_id} for PR #{pr_number}")
        return task_id
    
    # Fall back to generated ID
    logger.debug(f"No task found for PR #{pr_number}, using generated ID")
    return f"pr-{repository.replace('/', '-')}-{pr_number}"


@router.post("")
@router.post("/")
async def github_webhook(request: Request):
    """Handle GitHub webhook events.
    
    Processes:
    - issue_comment: Bot commands in PR comments
    - pull_request_review: Review approvals
    - push: CI status updates
    """
    # Validate webhook signature for security (skip in dev if no secret configured)
    print(f"DEBUG: Processing GitHub webhook. Secret configured: {bool(settings.GITHUB_WEBHOOK_SECRET)}", flush=True)
    
    if settings.GITHUB_WEBHOOK_SECRET:
        raw_payload = await verify_github_signature(request)
    else:
        logger.warning("GITHUB_WEBHOOK_SECRET not configured - skipping signature verification")
        print("DEBUG: Skipping signature verification", flush=True)
        raw_payload = await request.body()
    
    logger.info(f"Received payload size: {len(raw_payload)} bytes")
    print(f"DEBUG: Payload received, size: {len(raw_payload)}", flush=True)

    try:
        # Decode bytes to string first
        payload_str = raw_payload.decode('utf-8')
        
        # Handle form-encoded payload (application/x-www-form-urlencoded)
        if payload_str.startswith("payload="):
            payload_str = urllib.parse.unquote_plus(payload_str[8:])  # Remove 'payload=' prefix
            
        payload = json.loads(payload_str)
    except Exception as e:
        logger.error(f"Failed to decode JSON payload: {e}")
        logger.debug(f"Raw payload sample: {raw_payload[:100]}")
        return {"status": "error", "reason": "invalid json"}
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    
    logger.info(f"GitHub webhook received: {event_type}")
    
    # Handle PR comments for bot commands (only new comments, not edits)
    if "comment" in payload and "issue" in payload:
        action = payload.get("action", "")
        print(f"DEBUG: Comment action: {action}", flush=True)
        if action == "created":
            return await handle_pr_comment(payload)
        else:
            logger.debug(f"Ignoring comment action: {action}")
            return {"status": "ignored", "reason": f"comment action: {action}"}
    
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
    
    # Check if this mentions the bot
    mentions_bot = any(
        tag.lower() in comment_body.lower() 
        for tag in BOT_CONFIG.tags
    )
    
    if not mentions_bot:
        return {"status": "ignored", "reason": "no bot mention"}
    
    logger.info(
        f"PR comment from @{comment_author}: {comment_body[:100]}..."
    )

    # 1. Acknowledge immediately with "eyes" reaction
    if comment_id:
        owner, repo = repo_full_name.split("/")
        await github_client.add_reaction(
            owner=owner,
            repo=repo,
            comment_id=comment_id,
            reaction="eyes"
        )

    # Look up task ID from Redis (async)
    task_id = await get_task_id_for_pr(pr_number, repo_full_name)
    
    # Build context for command parser
    context = {
        "pr_number": pr_number,
        "repository": repo_full_name,
        "comment_id": comment_id,
        "author": comment_author,
        "pr_url": pr_url,
        "task_id": task_id,
        "pr_title": payload["issue"].get("title", ""),
        "pr_body": payload["issue"].get("body", ""),
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
        extra={"command_type": parsed.command_type.value, "command_args": parsed.args}
    )
    
    # Execute the command
    result = await command_executor.execute(parsed)
    
    logger.info(f"Command executed: {parsed.command_name} - success: {result.success}")
    
    # Post comment if specifically requested (e.g. results)
    if result.should_reply:
        owner, repo = repo_full_name.split("/")
        await github_client.post_comment(
            owner=owner,
            repo=repo,
            issue_number=pr_number,
            body=result.message
        )

    # 2. Add final reaction based on result
    if comment_id:
        owner, repo = repo_full_name.split("/")
        final_reaction = result.reaction or ("rocket" if result.success else "confused")
        await github_client.add_reaction(
            owner=owner,
            repo=repo,
            comment_id=comment_id,
            reaction=final_reaction
        )
    
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
        task_id = await get_task_id_for_pr(pr_number, repo_full_name)
        task_data = await queue.get_task(task_id)
        
        if task_data:
            await queue.update_task_status(task_id, TaskStatus.APPROVED)
            
            # Create typed task for execution queue
            pr_url = payload.get("pull_request", {}).get("html_url", "")
            exec_task = GitHubTask(
                repository=repo_full_name,
                pr_number=pr_number,
                pr_url=pr_url,
                action="approved"
            )
            await queue.push_task(settings.EXECUTION_QUEUE, exec_task)
            
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
