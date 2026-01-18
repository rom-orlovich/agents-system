"""
Webhook Server for Multiple-Agents System (Local)
==================================================
FastAPI-based webhook server for local testing.
"""

import json
import hashlib
import hmac
import os
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)


app = FastAPI(
    title="Multiple-Agents Webhook Server (Local)",
    description="Local webhook server for testing",
    version="0.1.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/tasks")
async def list_tasks():
    """List all tasks."""
    from local_runner import get_orchestrator
    orchestrator = get_orchestrator()
    tasks = orchestrator.task_store.scan()
    return {"tasks": tasks, "count": len(tasks)}


def verify_signature(source: str, headers: Dict[str, str], body: bytes) -> bool:
    """Verify webhook signature."""
    secret_env = f"{source.upper()}_WEBHOOK_SECRET"
    secret = os.environ.get(secret_env, "")
    if not secret:
        return True
    
    if source == "github":
        signature = headers.get("x-hub-signature-256", "")
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    
    elif source == "sentry":
        signature = headers.get("sentry-hook-signature", "")
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    
    elif source == "slack":
        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")
        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        expected = "v0=" + hmac.new(secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    
    return True


@app.post("/webhooks/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Jira webhook events."""
    body = await request.body()
    headers = dict(request.headers)
    
    if not verify_signature("jira", headers, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = json.loads(body)
    webhook_event = payload.get("webhookEvent", "")
    ai_label = os.environ.get("JIRA_AI_LABEL", "AI")
    
    logger.info("jira_webhook_received", event=webhook_event)
    
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    labels = [l.get("name", l) if isinstance(l, dict) else l for l in fields.get("labels", [])]
    
    should_process = False
    
    if webhook_event == "jira:issue_created" and ai_label in labels:
        should_process = True
    elif webhook_event == "jira:issue_updated":
        for item in payload.get("changelog", {}).get("items", []):
            if item.get("field") == "labels" and ai_label in item.get("toString", ""):
                should_process = True
                break
    
    if should_process:
        ticket = {
            "id": issue.get("key", "UNKNOWN"),
            "key": issue.get("key", "UNKNOWN"),
            "summary": fields.get("summary", ""),
            "description": fields.get("description", "") or "",
            "labels": labels,
            "priority": fields.get("priority", {}).get("name", "Medium") if isinstance(fields.get("priority"), dict) else "Medium"
        }
        background_tasks.add_task(run_workflow, ticket)
        return JSONResponse(content={"status": "accepted", "ticket": ticket["id"]}, status_code=202)
    
    return {"status": "ignored"}


@app.post("/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle GitHub webhook events."""
    body = await request.body()
    headers = dict(request.headers)
    
    if not verify_signature("github", headers, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = json.loads(body)
    event_type = headers.get("x-github-event", "")
    
    logger.info("github_webhook_received", event=event_type)
    
    if event_type == "workflow_run" and payload.get("action") == "completed":
        workflow_run = payload.get("workflow_run", {})
        prs = workflow_run.get("pull_requests", [])
        if prs:
            background_tasks.add_task(
                run_cicd,
                payload.get("repository", {}).get("name", ""),
                prs[0].get("number"),
                workflow_run.get("conclusion", "")
            )
            return JSONResponse(content={"status": "accepted"}, status_code=202)
    
    return {"status": "ignored"}


@app.post("/webhooks/sentry")
async def sentry_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Sentry webhook events."""
    body = await request.body()
    headers = dict(request.headers)
    
    if not verify_signature("sentry", headers, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = json.loads(body)
    action = payload.get("action", "")
    
    logger.info("sentry_webhook_received", action=action)
    
    if action in ("triggered", "created"):
        background_tasks.add_task(run_sentry)
        return JSONResponse(content={"status": "accepted"}, status_code=202)
    
    return {"status": "ignored"}


@app.post("/webhooks/slack")
async def slack_webhook(request: Request):
    """Handle Slack slash commands."""
    body = await request.body()
    headers = dict(request.headers)
    
    if not verify_signature("slack", headers, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    content_type = headers.get("content-type", "")
    
    if "application/x-www-form-urlencoded" in content_type:
        from urllib.parse import parse_qs
        params = parse_qs(body.decode())
        text = params.get("text", [""])[0]
        user_id = params.get("user_id", ["unknown"])[0]
    else:
        payload = json.loads(body)
        text = payload.get("text", "")
        user_id = payload.get("user_id", "unknown")
    
    parts = text.strip().split()
    cmd = parts[0] if parts else "help"
    args = parts[1:] if len(parts) > 1 else []
    
    from local_runner import get_orchestrator
    response = get_orchestrator().handle_slack_command(cmd, args, user_id)
    
    return {"response_type": "in_channel", "text": response}


def run_workflow(ticket: Dict[str, Any]):
    """Run workflow in background."""
    try:
        from local_runner import get_orchestrator
        get_orchestrator().run_full_workflow(ticket, auto_approve=True)
    except Exception as e:
        logger.error("workflow_failed", error=str(e))


def run_cicd(repo: str, pr_number: int, conclusion: str):
    """Run CI/CD in background."""
    try:
        from local_runner import get_orchestrator
        get_orchestrator().cicd.run({"repo": repo, "prNumber": pr_number, "conclusion": conclusion})
    except Exception as e:
        logger.error("cicd_failed", error=str(e))


def run_sentry():
    """Run Sentry monitoring in background."""
    try:
        from local_runner import get_orchestrator
        get_orchestrator().run_sentry_monitoring()
    except Exception as e:
        logger.error("sentry_failed", error=str(e))


def run_server(host: str = "0.0.0.0", port: int = 8001):
    """Run the webhook server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
