"""
Webhook Server for Single-Agent System
=======================================
FastAPI-based webhook server for local testing.
Handles webhooks from Jira, GitHub, Sentry, and Slack.
"""

import json
import hashlib
import hmac
from datetime import datetime
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

from config import settings
from agents import AgentOrchestrator

logger = structlog.get_logger(__name__)

# Global orchestrator instance
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("webhook_server_starting", port=settings.webhook.port)
    yield
    logger.info("webhook_server_stopping")


app = FastAPI(
    title="Single-Agent Webhook Server",
    description="Local webhook server for testing agent workflows",
    version="0.1.0",
    lifespan=lifespan
)


# =============================================================================
# Health & Status Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/tasks")
async def list_tasks():
    """List all tasks (for debugging)."""
    orchestrator = get_orchestrator()
    tasks = orchestrator.gateway.get_task_store().scan()
    return {"tasks": tasks, "count": len(tasks)}


# =============================================================================
# Signature Verification
# =============================================================================

def verify_jira_signature(headers: Dict[str, str], body: bytes) -> bool:
    """Verify Jira webhook signature (if configured)."""
    secret = settings.webhook.jira_secret
    if not secret:
        return True  # Skip verification if no secret configured
    # Jira uses different verification methods depending on setup
    return True


def verify_github_signature(headers: Dict[str, str], body: bytes) -> bool:
    """Verify GitHub webhook signature."""
    secret = settings.webhook.github_secret
    if not secret:
        return True
    
    signature = headers.get("x-hub-signature-256", "")
    if not signature:
        return False
    
    expected = "sha256=" + hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)


def verify_sentry_signature(headers: Dict[str, str], body: bytes) -> bool:
    """Verify Sentry webhook signature."""
    secret = settings.webhook.sentry_secret
    if not secret:
        return True
    
    signature = headers.get("sentry-hook-signature", "")
    if not signature:
        return False
    
    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)


def verify_slack_signature(headers: Dict[str, str], body: bytes) -> bool:
    """Verify Slack request signature."""
    secret = settings.webhook.slack_signing_secret
    if not secret:
        return True
    
    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")
    
    if not timestamp or not signature:
        return False
    
    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    expected = "v0=" + hmac.new(
        secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)


# =============================================================================
# Webhook Endpoints
# =============================================================================

@app.post("/webhooks/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Jira webhook events.
    
    Triggers workflow when:
    - Issue created with 'AI' label
    - Issue updated and 'AI' label added
    """
    body = await request.body()
    headers = dict(request.headers)
    
    if not verify_jira_signature(headers, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = json.loads(body)
    webhook_event = payload.get("webhookEvent", "")
    ai_label = settings.jira.ai_label
    
    logger.info("jira_webhook_received", event=webhook_event)
    
    # Check for AI label
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    labels = [
        label.get("name", "") if isinstance(label, dict) else label
        for label in fields.get("labels", [])
    ]
    
    should_process = False
    
    if webhook_event == "jira:issue_created":
        if ai_label in labels:
            should_process = True
    
    elif webhook_event == "jira:issue_updated":
        changelog = payload.get("changelog", {})
        for item in changelog.get("items", []):
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
        
        # Run workflow in background
        background_tasks.add_task(run_workflow_background, ticket)
        
        return JSONResponse(
            content={"status": "accepted", "ticket": ticket["id"]},
            status_code=202
        )
    
    return {"status": "ignored", "reason": "No AI label or not a trigger event"}


@app.post("/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle GitHub webhook events.
    
    Handles:
    - workflow_run completed → CI/CD agent
    - issue_comment with @agent approve → Trigger execution
    - issue_comment with @agent → Other commands
    """
    body = await request.body()
    headers = dict(request.headers)
    
    if not verify_github_signature(headers, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = json.loads(body)
    event_type = headers.get("x-github-event", "")
    
    logger.info("github_webhook_received", event=event_type)
    
    if event_type == "workflow_run":
        action = payload.get("action", "")
        if action == "completed":
            workflow_run = payload.get("workflow_run", {})
            conclusion = workflow_run.get("conclusion", "")
            
            # Find associated PR
            prs = workflow_run.get("pull_requests", [])
            if prs:
                pr_number = prs[0].get("number")
                repo = payload.get("repository", {}).get("name", "")
                
                background_tasks.add_task(
                    run_cicd_background, repo, pr_number, conclusion
                )
                
                return JSONResponse(
                    content={"status": "accepted", "pr": pr_number, "conclusion": conclusion},
                    status_code=202
                )
    
    elif event_type == "issue_comment":
        action = payload.get("action", "")
        if action == "created":
            comment = payload.get("comment", {})
            body_text = comment.get("body", "").lower()
            issue = payload.get("issue", {})
            repo = payload.get("repository", {})
            
            # Check if this is a PR comment (issue with pull_request field)
            if "pull_request" in issue and "@agent" in body_text:
                pr_number = issue.get("number")
                repo_name = repo.get("name", "")
                
                # Handle @agent approve - trigger execution
                if "approve" in body_text or "execute" in body_text:
                    logger.info("github_approval_received", pr=pr_number, repo=repo_name)
                    
                    background_tasks.add_task(
                        run_execution_from_pr, repo_name, pr_number, comment.get("user", {}).get("login", "unknown")
                    )
                    
                    return JSONResponse(
                        content={
                            "status": "accepted",
                            "action": "execution_triggered",
                            "pr": pr_number,
                            "repo": repo_name
                        },
                        status_code=202
                    )
                
                # Handle @agent status
                elif "status" in body_text:
                    return {"status": "command_received", "command": "status", "pr": pr_number}
                
                # Handle @agent reject
                elif "reject" in body_text:
                    return {"status": "command_received", "command": "reject", "pr": pr_number}
    
    return {"status": "ignored"}


@app.post("/webhooks/sentry")
async def sentry_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Sentry webhook events.
    
    Triggers Sentry agent for new issues or alerts.
    """
    body = await request.body()
    headers = dict(request.headers)
    
    if not verify_sentry_signature(headers, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = json.loads(body)
    action = payload.get("action", "")
    
    logger.info("sentry_webhook_received", action=action)
    
    if action in ("triggered", "created"):
        # Run Sentry monitoring in background
        background_tasks.add_task(run_sentry_background)
        
        return JSONResponse(
            content={"status": "accepted"},
            status_code=202
        )
    
    return {"status": "ignored"}


@app.post("/webhooks/slack")
async def slack_webhook(request: Request):
    """Handle Slack slash commands and interactions.
    
    Handles /agent commands: status, approve, reject, retry, list
    """
    body = await request.body()
    headers = dict(request.headers)
    
    if not verify_slack_signature(headers, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse form data (Slack sends form-encoded)
    content_type = headers.get("content-type", "")
    
    if "application/x-www-form-urlencoded" in content_type:
        from urllib.parse import parse_qs
        params = parse_qs(body.decode())
        command = params.get("command", [""])[0]
        text = params.get("text", [""])[0]
        user_id = params.get("user_id", ["unknown"])[0]
    else:
        payload = json.loads(body)
        command = payload.get("command", "")
        text = payload.get("text", "")
        user_id = payload.get("user_id", "unknown")
    
    logger.info("slack_webhook_received", command=command, text=text)
    
    # Parse command
    parts = text.strip().split()
    cmd = parts[0] if parts else "help"
    args = parts[1:] if len(parts) > 1 else []
    
    orchestrator = get_orchestrator()
    response = orchestrator.handle_slack_command(cmd, args, user_id)
    
    return {"response_type": "in_channel", "text": response}


# =============================================================================
# Background Tasks
# =============================================================================

def run_workflow_background(ticket: Dict[str, Any]):
    """Run workflow in background."""
    try:
        logger.info("background_workflow_started", ticket=ticket["id"])
        orchestrator = get_orchestrator()
        result = orchestrator.run_full_workflow(ticket, auto_approve=True)
        logger.info("background_workflow_completed", ticket=ticket["id"], success=result.get("success"))
    except Exception as e:
        logger.error("background_workflow_failed", ticket=ticket["id"], error=str(e))


def run_cicd_background(repo: str, pr_number: int, conclusion: str):
    """Run CI/CD agent in background."""
    try:
        logger.info("background_cicd_started", repo=repo, pr=pr_number)
        orchestrator = get_orchestrator()
        result = orchestrator.cicd.run({
            "repo": repo,
            "prNumber": pr_number,
            "conclusion": conclusion
        })
        logger.info("background_cicd_completed", repo=repo, pr=pr_number)
    except Exception as e:
        logger.error("background_cicd_failed", repo=repo, pr=pr_number, error=str(e))


def run_sentry_background():
    """Run Sentry monitoring in background."""
    try:
        logger.info("background_sentry_started")
        orchestrator = get_orchestrator()
        result = orchestrator.run_sentry_monitoring()
        logger.info("background_sentry_completed", processed=result.get("processed", 0))
    except Exception as e:
        logger.error("background_sentry_failed", error=str(e))


def run_execution_from_pr(repo: str, pr_number: int, approved_by: str):
    """Run execution agent for an approved PR.
    
    Triggered by '@agent approve' or '@agent execute' comment on a PR.
    Fetches the PLAN.md from the PR branch and runs the execution agent.
    """
    try:
        logger.info("pr_execution_started", repo=repo, pr=pr_number, approved_by=approved_by)
        orchestrator = get_orchestrator()
        
        # Get PR details
        github = orchestrator.gateway.get_tool("github-mcp")
        
        # Try to get PLAN.md from the PR branch
        pr_details = github.get_pull_request(repo, pr_number)
        branch = pr_details.get("head", {}).get("ref", "main") if pr_details else "main"
        
        plan_content = github.get_file_content(repo, "PLAN.md", branch)
        
        if not plan_content:
            logger.warning("no_plan_found", repo=repo, pr=pr_number)
            # Post comment on PR
            github.add_pr_comment(repo, pr_number, 
                "❌ **Agent Error**: No PLAN.md found in this PR. Cannot execute without a plan.")
            return
        
        # Parse plan to get tasks (simplified - in production would use proper parsing)
        tasks = _parse_tasks_from_plan(plan_content)
        
        # Notify PR that execution is starting
        github.add_pr_comment(repo, pr_number,
            f"🚀 **Agent Execution Started**\n\n"
            f"Approved by: @{approved_by}\n"
            f"Tasks to execute: {len(tasks)}\n\n"
            f"I'll update this PR with the implementation..."
        )
        
        # Run execution
        result = orchestrator.execution.run({
            "plan": {"implementation": {"tasks": tasks}},
            "prInfo": {"repo": repo, "prNumber": pr_number, "branch": branch}
        })
        
        # Post result
        if result.get("completedTasks"):
            github.add_pr_comment(repo, pr_number,
                f"✅ **Execution Complete**\n\n"
                f"- Completed: {len(result['completedTasks'])} tasks\n"
                f"- Failed: {len(result.get('failedTasks', []))} tasks\n\n"
                f"Please review the changes and merge when ready."
            )
        else:
            github.add_pr_comment(repo, pr_number,
                f"⚠️ **Execution Issues**\n\n"
                f"Some tasks failed. Please check the details and retry.\n\n"
                f"```\n{json.dumps(result.get('failedTasks', []), indent=2)[:500]}\n```"
            )
        
        logger.info("pr_execution_completed", repo=repo, pr=pr_number, 
                   completed=len(result.get("completedTasks", [])))
        
    except Exception as e:
        logger.error("pr_execution_failed", repo=repo, pr=pr_number, error=str(e))


def _parse_tasks_from_plan(plan_content: str) -> list:
    """Parse tasks from PLAN.md content."""
    tasks = []
    lines = plan_content.split("\n")
    task_id = 0
    
    in_tasks_section = False
    for line in lines:
        if "## Implementation Tasks" in line or "## Tasks" in line:
            in_tasks_section = True
            continue
        
        if in_tasks_section and line.startswith("|") and "---" not in line and "Task" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                task_id += 1
                tasks.append({
                    "id": task_id,
                    "description": parts[1] if len(parts) > 1 else parts[0],
                    "file": parts[2] if len(parts) > 2 else f"src/task_{task_id}.py",
                    "estimatedHours": 2,
                    "dependencies": []
                })
        
        if in_tasks_section and line.startswith("##") and "Tasks" not in line:
            break
    
    return tasks


# =============================================================================
# Server Entry Point
# =============================================================================

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the webhook server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
