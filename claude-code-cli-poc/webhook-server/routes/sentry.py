"""
Sentry Webhook Handler
======================
Handles incoming webhooks from Sentry.
"""

import hashlib
import structlog
from fastapi import APIRouter, Header, HTTPException, Request

from shared.config import get_settings
from webhook_server.queue import get_queue

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("")
async def handle_sentry_webhook(
    request: Request,
    sentry_hook_signature: str | None = Header(None),
):
    """
    Handle Sentry webhook events.
    
    Triggered when:
    - New issue created
    - Issue exceeds alert threshold
    """
    settings = get_settings()
    body = await request.body()
    
    # Validate signature if secret is configured
    if settings.sentry.webhook_secret and sentry_hook_signature:
        expected = hashlib.sha256(
            f"{settings.sentry.webhook_secret}{body.decode()}".encode()
        ).hexdigest()
        if sentry_hook_signature != expected:
            logger.warning("Invalid Sentry webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse Sentry webhook payload", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Extract event details
    action = payload.get("action", "")
    data = payload.get("data", {})
    issue = data.get("issue", {})
    event = data.get("event", {})
    
    logger.info(
        "Received Sentry webhook",
        action=action,
        issue_id=issue.get("id"),
    )
    
    # Only process new issues or triggered alerts
    if action not in ["created", "triggered"]:
        logger.debug("Ignoring Sentry action", action=action)
        return {"status": "ignored", "reason": f"Action {action} not handled"}
    
    # Extract error information
    error_info = extract_error_info(issue, event)
    
    # Queue task for planning agent
    queue = get_queue()
    task_data = {
        "source": "sentry",
        "ticket_id": f"SENTRY-{issue.get('id', 'unknown')}",
        "summary": f"[Sentry] {error_info['title']}",
        "description": build_description(error_info),
        "priority": error_info["level"],
        "labels": ["sentry", "auto-generated"],
        "sentry_link": error_info["sentry_link"],
    }
    
    queue.enqueue_planning_task(task_data)
    
    return {
        "status": "queued",
        "issue_id": issue.get("id"),
        "message": "Task queued for planning agent",
    }


def extract_error_info(issue: dict, event: dict) -> dict:
    """Extract relevant error information from Sentry payload."""
    # Get stack trace
    stacktrace = ""
    exception = event.get("exception", {})
    if exception and "values" in exception:
        for exc in exception["values"]:
            stacktrace += f"\n{exc.get('type', 'Error')}: {exc.get('value', '')}\n"
            if "stacktrace" in exc:
                for frame in exc["stacktrace"].get("frames", [])[-5:]:
                    stacktrace += (
                        f"  at {frame.get('filename', '?')}:{frame.get('lineno', '?')} "
                        f"in {frame.get('function', '?')}\n"
                    )
    
    # Get tags
    tags = {t["key"]: t["value"] for t in event.get("tags", [])}
    
    # Get breadcrumbs
    breadcrumbs = event.get("breadcrumbs", {}).get("values", [])[-5:]
    breadcrumb_text = "\n".join([
        f"  [{b.get('category', '?')}] {b.get('message', '')}"
        for b in breadcrumbs
    ])
    
    return {
        "title": issue.get("title", "Unknown Error"),
        "culprit": issue.get("culprit", ""),
        "level": issue.get("level", "error"),
        "first_seen": issue.get("firstSeen", ""),
        "count": issue.get("count", 1),
        "sentry_link": issue.get("permalink", ""),
        "stacktrace": stacktrace,
        "breadcrumbs": breadcrumb_text,
        "environment": tags.get("environment", "unknown"),
        "release": tags.get("release", "unknown"),
    }


def build_description(error_info: dict) -> str:
    """Build a description from error info."""
    return f"""## Error Details

**Error:** {error_info['title']}
**Location:** {error_info['culprit']}
**Level:** {error_info['level']}
**Environment:** {error_info['environment']}
**Occurrences:** {error_info['count']}

## Stack Trace
```
{error_info['stacktrace']}
```

## Recent Activity
```
{error_info['breadcrumbs']}
```

## Links
- [Sentry Issue]({error_info['sentry_link']})
"""
