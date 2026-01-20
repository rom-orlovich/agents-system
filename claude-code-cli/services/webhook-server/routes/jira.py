"""Jira webhook routes."""

import sys
import re
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import logging

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.config import settings
from shared.models import TaskSource
from shared.task_queue import RedisQueue
from shared.constants import BOT_CONFIG

router = APIRouter()
queue = RedisQueue()
logger = logging.getLogger("jira-webhook")


def extract_sentry_issue_id(description: str) -> Optional[str]:
    """Extract Sentry issue ID from Jira ticket description.
    
    Sentry creates tickets with a link like:
    "Sentry Issue: [JAVASCRIPT-REACT-1](https://sentry.io/...)"
    or just "Sentry Issue: JAVASCRIPT-REACT-1"
    
    Args:
        description: Jira ticket description text
        
    Returns:
        Sentry issue ID (e.g., "JAVASCRIPT-REACT-1") or None
    """
    if not description:
        return None
    
    # Pattern 1: Markdown link format [ISSUE-ID](url)
    pattern1 = r"Sentry Issue:\s*\[([A-Z]+-[A-Z]+-\d+)\]"
    match = re.search(pattern1, description, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 2: Plain text format "Sentry Issue: ISSUE-ID"
    pattern2 = r"Sentry Issue:\s*([A-Z]+-[A-Z]+-\d+)"
    match = re.search(pattern2, description, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 3: Just look for the issue ID pattern anywhere
    pattern3 = r"([A-Z]+-[A-Z]+-\d+)"
    match = re.search(pattern3, description)
    if match:
        return match.group(1)
    
    return None


def extract_repository_from_description(description: str) -> Optional[str]:
    """Extract repository name from Jira ticket description.
    
    Look for patterns like:
    - "Repository: owner/repo"
    - "github.com/owner/repo"
    
    Args:
        description: Jira ticket description text
        
    Returns:
        Repository name (e.g., "rom-orlovich/manga-creator") or None
    """
    if not description:
        return None
    
    # Pattern 1: GitHub URL
    pattern1 = r"github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)"
    match = re.search(pattern1, description)
    if match:
        return match.group(1)
    
    # Pattern 2: Repository: owner/repo
    pattern2 = r"[Rr]epository:\s*([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)"
    match = re.search(pattern2, description)
    if match:
        return match.group(1)
    
    return None


@router.post("")
@router.post("/")
async def jira_webhook(request: Request):
    """Handle Jira webhook events.
    
    Processes:
    1. Tickets created by Sentry integration (auto-enrichment)
    2. Tickets with AI-Fix label (manual requests)
    3. Ticket transitions to "Approved" status (approval flow)
    
    Returns:
        Response dict with status and task info
    """
    try:
        payload = await request.json()
        
        # Extract webhook event type
        webhook_event = payload.get("webhookEvent", "")
        issue = payload.get("issue", {})
        issue_key = issue.get("key", "")
        fields = issue.get("fields", {})
        
        # Get description (might be in different formats)
        description = fields.get("description", "")
        if isinstance(description, dict):
            # Atlassian Document Format (ADF)
            description = str(description.get("content", ""))
        
        summary = fields.get("summary", "")
        labels = fields.get("labels", [])
        status = fields.get("status", {}).get("name", "")
        
        assignee_obj = fields.get("assignee") or {}
        
        # Log the full assignee object for debugging
        print(f"DEBUG: Jira Assignee Object: {assignee_obj}")
      
        assignee_name = (assignee_obj.get("displayName") or 
                         assignee_obj.get("name") or 
                         assignee_obj.get("accountId") or "")
        
        bot_username = BOT_CONFIG.jira_username
        is_assigned_to_bot = (assignee_name.lower() == bot_username.lower() or 
                              bot_username.lower() in assignee_name.lower())

        print(f"📨 Jira webhook received: {webhook_event} for {issue_key}")
        print(f"   Summary: {summary}")
        print(f"   Status: {status}")
        print(f"   Assignee: '{assignee_name}' (Bot: '{bot_username}', Match: {is_assigned_to_bot})")
        print(f"   Labels: {labels}")
        
        # Detect if this ticket was created by Sentry
        sentry_issue_id = extract_sentry_issue_id(description)
        is_sentry_ticket = sentry_issue_id is not None or "sentry" in summary.lower()
        
        # Extract repository if available
        repository = extract_repository_from_description(description)
        
        # CASE 1: Ticket transitioned to "Approved" - trigger execution
        if webhook_event == "jira:issue_updated" and status.lower() in ["approved", "in progress"]:
            # Check if this is an approval transition
            changelog = payload.get("changelog", {})
            items = changelog.get("items", [])
            
            for item in items:
                if item.get("field") == "status" and item.get("toString", "").lower() in ["approved", "in progress"]:
                    print(f"✅ Ticket {issue_key} approved via Jira status transition")
                    
                    task_data = {
                        "source": TaskSource.JIRA.value,
                        "action": "approve",
                        "issue_key": issue_key,
                        "sentry_issue_id": sentry_issue_id,
                        "repository": repository
                    }
                    
                    task_id = await queue.push(settings.EXECUTION_QUEUE, task_data)
                    
                    return {
                        "status": "approved",
                        "task_id": task_id,
                        "issue_key": issue_key
                    }
        
        # CASE 2: Sentry-created ticket or assigned to bot - trigger enrichment
        if (webhook_event == "jira:issue_created" and (is_sentry_ticket or is_assigned_to_bot)) or \
           (webhook_event == "jira:issue_updated" and is_assigned_to_bot):
            
            # Check if this was a fresh assignment to the bot
            is_assignment_event = False
            if webhook_event == "jira:issue_updated":
                changelog = payload.get("changelog", {})
                items = changelog.get("items", [])
                for item in items:
                    if item.get("field") == "assignee" and bot_username.lower() in str(item.get("toString", "")).lower():
                        is_assignment_event = True
                        break
            
            # Only trigger enrichment if it's sentry OR assigned to bot
            if is_sentry_ticket:
                print(f"🔗 Detected Sentry ticket: {sentry_issue_id}")
                action = "enrich"
                status_msg = "queued_for_enrichment"
            else:
                print(f"👤 Ticket assigned to agent: {issue_key}")
                action = "fix"
                status_msg = "queued"

            task_data = {
                "source": TaskSource.JIRA.value,
                "action": action,
                "description": summary,
                "issue_key": issue_key,
                "sentry_issue_id": sentry_issue_id,
                "repository": repository,
                "full_description": description[:10000]
            }
            
            task_id = await queue.push(settings.PLANNING_QUEUE, task_data)
            
            print(f"📥 Jira task queued: {task_id} (Issue: {issue_key}, Action: {action})")
            
            return {
                "status": status_msg,
                "task_id": task_id,
                "issue_key": issue_key,
                "sentry_issue_id": sentry_issue_id
            }
        
        # CASE 3: Manual AI-Fix request (via label) - fallback
        if webhook_event == "jira:issue_created" and "AI-Fix" in labels:
            task_data = {
                "source": TaskSource.JIRA.value,
                "action": "fix",
                "description": summary,
                "issue_key": issue_key,
                "repository": repository
            }
            
            task_id = await queue.push(settings.PLANNING_QUEUE, task_data)
            
            print(f"📥 Manual AI-Fix (via label) queued: {task_id} (Issue: {issue_key})")
            
            return {
                "status": "queued",
                "task_id": task_id,
                "issue_key": issue_key
            }
        
        # Not a relevant event
        return {
            "status": "ignored",
            "reason": "Not a Sentry ticket or AI-Fix request",
            "webhook_event": webhook_event,
            "issue_key": issue_key
        }

    except Exception as e:
        print(f"❌ Error processing Jira webhook: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test")
async def test_jira_webhook():
    """Test endpoint for Jira webhook."""
    return {"status": "Jira webhook endpoint is working"}

