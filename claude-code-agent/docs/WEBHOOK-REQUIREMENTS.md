# Webhook System Requirements

## 📋 Summary of All Requirements

This document captures all requirements discussed for the webhook system implementation.

**Key Requirements**:
1. ✅ Hard-coded configuration (not database-driven)
2. ✅ Type-safe with Pydantic validation
3. ✅ Individual typed variables (not in list)
4. ✅ Simple endpoints: `/webhooks/github` (OLD Claude Code CLI pattern)
5. ✅ One file per provider (not per webhook type)
6. ✅ Separate functions per provider (no combo functions)
7. ✅ Aligned with OLD Claude Code CLI structure
8. ✅ Command matching by name/aliases (not trigger/action)
9. ✅ Immediate response before task queue
10. ✅ Easy add/remove (just add/delete file)
11. ✅ Validation at startup
12. ✅ `{{variable}}` template syntax
13. ✅ Environment variables for secrets
14. ✅ **TDD approach** - Write tests first, then implement
15. ✅ **Slack notifications** - Send notification after each task completion

---

## 1. ✅ Hard-Coded Configuration (Not Dynamic/Database-Driven)

**Requirement**: Webhooks should be hard-coded in code, not stored in database or created via API.

**Rationale**: 
- Easier to understand and maintain
- Version controlled in git
- Type-safe with validation
- No API calls needed to create webhooks

**Implementation**:
- Webhooks defined in `core/webhook_configs.py`
- Individual typed variables (not in a list)
- Validated at startup

---

## 2. ✅ Type-Safe and Enforced

**Requirement**: Webhook configurations must be type-safe with Pydantic validation.

**Requirements**:
- Use Pydantic models for validation
- Type checking at development time
- Validation errors caught at startup
- No runtime errors from invalid configs

**Implementation**:
- Use `WebhookConfig` and `WebhookCommand` from `shared/machine_models.py`
- Pydantic field validators
- Startup validation function

---

## 3. ✅ Individual Typed Variables (Not in List)

**Requirement**: Each webhook should be an individual typed variable, not inside a list.

**Example**:
```python
# ✅ CORRECT - Individual variables
GITHUB_ISSUES_WEBHOOK: WebhookConfig = WebhookConfig(...)
GITHUB_PR_WEBHOOK: WebhookConfig = WebhookConfig(...)
JIRA_ISSUES_WEBHOOK: WebhookConfig = WebhookConfig(...)

# Collected for iteration
WEBHOOK_CONFIGS: List[WebhookConfig] = [
    GITHUB_ISSUES_WEBHOOK,
    GITHUB_PR_WEBHOOK,
    JIRA_ISSUES_WEBHOOK,
]
```

**Not**:
```python
# ❌ WRONG - All in list
WEBHOOK_CONFIGS: List[WebhookConfig] = [
    WebhookConfig(...),
    WebhookConfig(...),
]
```

**Benefits**:
- Clear, self-documenting names
- Easy to add/remove (just add/delete variable)
- Type checking per variable
- Better IDE support

---

## 4. ✅ Separate Endpoint for Each Webhook (OLD Claude Code CLI Pattern)

**Requirement**: Each webhook must have its own unique endpoint path, matching OLD Claude Code CLI pattern.

**OLD Claude Code CLI Pattern** (from `shared/machine_models.py`):
```python
endpoint: str = Field(..., pattern=r"^/webhooks/[a-z0-9-]+$")
```

**Required Format** (Simple, per provider):
```
POST /webhooks/github
POST /webhooks/jira
POST /webhooks/slack
POST /webhooks/sentry
POST /webhooks/gitlab
```

**NOT**:
```
❌ POST /webhooks/github/issues  (sub-paths not in OLD pattern)
❌ POST /webhooks/github/pr      (sub-paths not in OLD pattern)
❌ POST /webhooks/{provider}     (generic endpoint)
```

**Rationale**:
- Matches OLD Claude Code CLI pattern exactly
- Simple, clear endpoints
- One endpoint per provider/source
- Pattern: `/webhooks/[a-z0-9-]+` (no sub-paths)

---

## 5. ✅ Separate Route and Logic for Each Webhook

**Requirement**: Each webhook must have its own dedicated route handler with its own specific logic. NO combined/combo functions.

**NOT Generic/Implicit/Combined**:
```python
# ❌ WRONG - Generic handler
@router.post("/{provider}")
async def generic_webhook_handler(provider: str, ...):
    # Generic logic that tries to match commands
    config = get_webhook_by_endpoint(...)
    command = match_command(...)
    # Generic execution
```

**NOT Combined Functions**:
```python
# ❌ WRONG - Combined verification function
async def verify_webhook_signature(config, request, body):
    # Generic verification for all webhooks
    if config.source == "github":
        # GitHub verification
    elif config.source == "slack":
        # Slack verification
    # etc...
```

**REQUIRED - Separate Functions for Each Webhook**:
```python
# ✅ CORRECT - Separate handler for each webhook
@router.post("/github/issues")
async def github_issues_webhook(request: Request, ...):
    # Specific logic for GitHub issues ONLY
    # Handle issues.opened event
    # Post immediate reaction
    # Create task with specific template
    pass

@router.post("/github/pr")
async def github_pr_webhook(request: Request, ...):
    # Specific logic for GitHub PRs ONLY
    # Handle pull_request.opened event
    # Post immediate comment
    # Create task with PR-specific template
    pass

@router.post("/jira/issues")
async def jira_issues_webhook(request: Request, ...):
    # Specific logic for Jira issues ONLY
    # Handle jira:issue_created event
    # Post immediate comment
    # Create task with Jira-specific template
    pass
```

**REQUIRED - Separate Verification Functions**:
```python
# ✅ CORRECT - Separate verification for each webhook type
async def verify_github_signature(request: Request, body: bytes, secret: str):
    """Verify GitHub webhook signature ONLY."""
    signature_header = request.headers.get("X-Hub-Signature-256")
    # GitHub-specific verification logic
    pass

async def verify_slack_signature(request: Request, body: bytes, secret: str):
    """Verify Slack webhook signature ONLY."""
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    # Slack-specific verification logic
    pass

async def verify_jira_signature(request: Request, body: bytes, secret: str):
    """Verify Jira webhook signature ONLY."""
    # Jira-specific verification logic
    pass
```

**REQUIRED - Separate Immediate Response Functions**:
```python
# ✅ CORRECT - Separate immediate response for each webhook
async def send_github_issues_immediate_response(payload: dict, command: WebhookCommand):
    """Send immediate response for GitHub issues ONLY."""
    # GitHub issues-specific response logic
    # Add reaction or post comment
    pass

async def send_github_pr_immediate_response(payload: dict, command: WebhookCommand):
    """Send immediate response for GitHub PRs ONLY."""
    # GitHub PR-specific response logic
    pass

async def send_jira_issues_immediate_response(payload: dict, command: WebhookCommand):
    """Send immediate response for Jira issues ONLY."""
    # Jira-specific response logic
    pass
```

**Benefits**:
- Clear, explicit logic per webhook
- Easy to understand what each webhook does
- Easy to modify one webhook without affecting others
- Better error handling per webhook type
- No implicit command matching needed
- No shared/combo functions that handle multiple webhook types
- Each function has single responsibility

---

## 6. ✅ Align with OLD Claude Code CLI Structure

**Requirement**: Webhook structure must match the old Claude Code CLI project exactly.

**Required Structure**:

### WebhookConfig Model
```python
class WebhookConfig(BaseModel):
    name: str                           # Unique name
    endpoint: str                       # "/webhooks/github", "/webhooks/jira" (pattern: ^/webhooks/[a-z0-9-]+$)
    source: Literal[...]                # "github", "jira", "slack", "sentry" (NOT "provider")
    description: str
    target_agent: str                  # Default agent
    command_prefix: str                # "@agent", "/claude"
    commands: List[WebhookCommand]
    default_command: Optional[str]      # Fallback command
    requires_signature: bool
    signature_header: Optional[str]
    secret_env_var: Optional[str]      # Environment variable name
    is_builtin: bool
```

### WebhookCommand Model
```python
class WebhookCommand(BaseModel):
    name: str                          # Command name (NOT "trigger")
    aliases: List[str]                 # Alternative names
    description: str
    target_agent: str                  # Agent (NOT "agent")
    prompt_template: str              # Template (NOT "template")
    requires_approval: bool
```

**Key Differences from Current System**:
- ❌ NOT `trigger` + `action` system
- ✅ USE `name` + `aliases` system
- ❌ NOT `provider` field
- ✅ USE `source` field
- ❌ NOT `template` field
- ✅ USE `prompt_template` field
- ❌ NOT `agent` field
- ✅ USE `target_agent` field

---

## 7. ✅ Command Matching System (OLD System)

**Requirement**: Commands must be matched using name/aliases and command_prefix, not trigger/action.

**Matching Logic**:
1. Extract text from payload
2. Check if `command_prefix` is present (e.g., "@agent")
3. Find command by `name` or `aliases` in text
4. Fallback to `default_command` if no match

**Example**:
```python
# User comment: "@agent analyze this issue"
# 1. Find "@agent" prefix ✓
# 2. Find "analyze" command name ✓
# 3. Match command with name="analyze"
# 4. Execute command
```

**NOT**:
```python
# ❌ OLD trigger/action system
trigger="issues.opened"
action="create_task"
```

---

## 8. ✅ Immediate Response Before Task Queue

**Requirement**: Send immediate acknowledgment to user BEFORE task is sent to queue.

**Flow**:
```
1. Webhook received
2. Command matched
3. ⚡ IMMEDIATE RESPONSE sent ← NEW!
4. Task created
5. Task queued
6. Task processed (async)
```

**Immediate Responses by Provider**:

### GitHub Issues
- **Comments**: Add 👀 (eyes) reaction to comment
- **Issues**: Post quick comment `👀 Processing your 'analyze' request...`

### GitHub PRs
- **PR Comments**: Add 👀 reaction
- **PRs**: Post quick comment `👀 Reviewing your PR...`

### Jira Issues
- Post quick comment `🤖 Processing your request...`

### Slack Commands
- Send ephemeral response `🤖 Processing your 'help' request...`

### Sentry Errors
- Log acknowledgment

**Benefits**:
- Instant user feedback
- Better UX (no silent waiting)
- Non-blocking (doesn't delay task creation)
- Error handling (if response fails, task still created)

---

## 9. ✅ Developer-Friendly Add/Remove

**Requirement**: Developers must be able to easily add or remove webhooks.

**How to Add**:
```python
# 1. In core/webhook_configs.py - Create new typed variable
MY_NEW_WEBHOOK: WebhookConfig = WebhookConfig(
    name="my-webhook",
    endpoint="/webhooks/github/custom",  # Unique endpoint
    source="github",
    target_agent="planning",
    command_prefix="@agent",
    commands=[
        WebhookCommand(
            name="do-something",
            aliases=["action"],
            target_agent="planning",
            prompt_template="Do something: {{issue.title}}"
        )
    ],
    default_command="do-something",
    secret_env_var="GITHUB_WEBHOOK_SECRET",
)

# 2. Add to WEBHOOK_CONFIGS list
WEBHOOK_CONFIGS: List[WebhookConfig] = [
    GITHUB_ISSUES_WEBHOOK,
    # ... existing ...
    MY_NEW_WEBHOOK,  # Add here
]

# 3. Create NEW FILE: api/webhooks/github.py (or modify existing)
# Contains: route handler + verify + respond + match + create functions
# Route: @router.post("/github") → endpoint: /webhooks/github
# See example structure above

# 4. Register router in api/webhooks/__init__.py
from .github import router as github_router
router.include_router(github_router, prefix="/webhooks")
```

**How to Remove**:
- Delete the config variable (e.g., `MY_NEW_WEBHOOK`)
- Remove from `WEBHOOK_CONFIGS` list
- Delete or modify the file: `api/webhooks/github.py` (if it was provider-specific)
- Remove router registration from `api/webhooks/__init__.py`

---

## 10. ✅ Validation at Startup

**Requirement**: All webhook configurations must be validated at application startup.

**Validations**:
- ✅ No duplicate endpoints
- ✅ No duplicate names
- ✅ Valid endpoint pattern: `/webhooks/[a-z0-9-]+` (matches OLD Claude Code CLI pattern)
- ✅ Valid source values
- ✅ All commands have valid structure

**Error Handling**:
- Validation errors prevent startup
- Clear error messages
- Type checking catches errors early

---

## 11. ✅ Template Syntax

**Requirement**: Use `{{variable}}` syntax for templates (double braces).

**Example**:
```python
prompt_template="New issue: {{issue.title}}\n\n{{issue.body}}"
```

**NOT**:
```python
# ❌ Single braces
prompt_template="New issue: {issue.title}"
```

---

## 12. ✅ Environment Variables for Secrets

**Requirement**: Webhook secrets must use environment variables, not hard-coded values.

**Format**:
```python
secret_env_var="GITHUB_WEBHOOK_SECRET"  # References .env variable
```

**NOT**:
```python
# ❌ Hard-coded secret
secret="my-secret-123"
```

**Environment Variables**:
- `GITHUB_WEBHOOK_SECRET`
- `JIRA_WEBHOOK_SECRET`
- `SLACK_WEBHOOK_SECRET`
- `SENTRY_WEBHOOK_SECRET`

---

## 13. ✅ File Structure - One File Per Webhook

**Requirement**: Each webhook must have its own dedicated file containing the route handler and all its supporting functions.

**Structure**:
```
core/
  webhook_configs.py    # ← Hard-coded webhook configs (add/remove here)
  webhook_engine.py     # Shared execution logic (if needed)

api/
  webhooks/
    __init__.py         # Router registration
    github.py           # ← GitHub webhook (route + all functions) - endpoint: /webhooks/github
    jira.py             # ← Jira webhook (route + all functions) - endpoint: /webhooks/jira
    slack.py            # ← Slack webhook (route + all functions) - endpoint: /webhooks/slack
    sentry.py           # ← Sentry webhook (route + all functions) - endpoint: /webhooks/sentry
  webhooks_dynamic.py   # Old receiver (database-driven, backward compat)
```

**Note**: OLD Claude Code CLI uses simple endpoints per provider:
- `/webhooks/github` (handles all GitHub events: issues, PRs, comments)
- `/webhooks/jira` (handles all Jira events)
- `/webhooks/slack` (handles all Slack events)
- `/webhooks/sentry` (handles all Sentry events)

**Each File Contains**:
```python
# api/webhooks/github.py  (OLD pattern: one file per provider, not per webhook type)

# 1. Imports
from fastapi import APIRouter, Request, HTTPException
from core.webhook_configs import GITHUB_ISSUES_WEBHOOK
# ... other imports

router = APIRouter()

# 2. Verification function (for this webhook ONLY)
async def verify_github_issues_signature(request: Request, body: bytes) -> None:
    """Verify GitHub issues webhook signature ONLY."""
    # GitHub issues-specific verification logic
    pass

# 3. Immediate response function (for this webhook ONLY)
async def send_github_issues_immediate_response(payload: dict, command: WebhookCommand) -> bool:
    """Send immediate response for GitHub issues ONLY."""
    # GitHub issues-specific response logic
    pass

# 4. Command matching function (for this webhook ONLY)
def match_github_issues_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match command for GitHub issues ONLY."""
    # GitHub issues-specific matching logic
    pass

# 5. Task creation function (for this webhook ONLY)
async def create_github_issues_task(command: WebhookCommand, payload: dict, db: AsyncSession) -> str:
    """Create task for GitHub issues ONLY."""
    # GitHub issues-specific task creation
    pass

# 6. Route handler (for this webhook ONLY)
@router.post("/github/issues")
async def github_issues_webhook(request: Request, db: AsyncSession):
    """
    Dedicated handler for GitHub issues webhook.
    All logic and functions in this file.
    """
    # 1. Verify signature
    await verify_github_issues_signature(request, body)
    
    # 2. Parse payload
    payload = await request.json()
    
    # 3. Extract event type
    event_type = request.headers.get("X-GitHub-Event")
    
    # 4. Match command
    command = match_github_command(payload, event_type)
    
    # 5. Send immediate response
    await send_github_immediate_response(payload, command, event_type)
    
    # 6. Create task
    task_id = await create_github_task(command, payload, db)
    
    # 7. Queue task
    await redis_client.push_task(task_id)
    
    return {"status": "processed", "task_id": task_id}
```

**Router Registration**:
```python
# api/webhooks/__init__.py

from fastapi import APIRouter
from .github import router as github_router
from .jira import router as jira_router
from .slack import router as slack_router
from .sentry import router as sentry_router

router = APIRouter()

# Register all webhook routers (OLD pattern: one router per provider)
router.include_router(github_router, prefix="/webhooks")
router.include_router(jira_router, prefix="/webhooks")
router.include_router(slack_router, prefix="/webhooks")
router.include_router(sentry_router, prefix="/webhooks")
```

**Benefits**:
- Complete isolation: Each webhook is self-contained
- Easy to find: All code for one webhook in one file
- Easy to modify: Change one webhook without affecting others
- Clear structure: Everything related to a webhook is together
- Easy to add/remove: Just add/delete a file

---

## 14. ✅ Backward Compatibility

**Requirement**: Old database-driven system should still work.

**Implementation**:
- Keep `webhooks_dynamic.py` for backward compatibility
- New hard-coded system in separate routes
- Both can coexist
- Gradual migration path

---

## 📊 Summary Checklist

- [x] Hard-coded (not database-driven)
- [x] Type-safe with Pydantic
- [x] Individual typed variables (not in list)
- [x] Separate endpoint for each webhook
- [x] Separate route and logic for each webhook (NOT generic/implicit)
- [x] **One file per webhook** (route + all supporting functions)
- [x] **NO combo/shared functions** - each webhook has its own functions
- [x] Aligned with OLD Claude Code CLI structure
- [x] Command matching by name/aliases (not trigger/action)
- [x] Immediate response before task queue
- [x] Easy add/remove for developers (just add/delete file)
- [x] Validation at startup
- [x] `{{variable}}` template syntax
- [x] Environment variables for secrets
- [x] Clear file structure (one file = one webhook)
- [x] Backward compatibility

---

## 🎯 Final Structure Example

### File Structure
```
api/
  webhooks/
    __init__.py         # Router registration
    github.py           # Complete GitHub webhook (handles issues, PRs, comments)
    jira.py             # Complete Jira webhook (handles all Jira events)
    slack.py            # Complete Slack webhook (handles commands, mentions)
    sentry.py           # Complete Sentry webhook (handles all Sentry events)
```

### Example: GitHub Webhook File

```python
# api/webhooks/github.py

"""
GitHub Webhook Handler
Complete implementation: route + all supporting functions
Handles all GitHub events: issues, PRs, comments
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import hmac
import hashlib
import os
import json
import uuid
from datetime import datetime
from typing import Optional

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB, SessionDB, TaskDB
from core.database.redis_client import redis_client
from core.webhook_configs import GITHUB_ISSUES_WEBHOOK
from core.webhook_engine import render_template
from core.github_client import github_client
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType
import structlog

logger = structlog.get_logger()
router = APIRouter()


# ✅ Verification function (GitHub webhook ONLY)
async def verify_github_signature(request: Request, body: bytes) -> None:
    """Verify GitHub webhook signature ONLY."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="GITHUB_WEBHOOK_SECRET not configured")
    
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    
    if not hmac.compare_digest(f"sha256={expected}", signature_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


# ✅ Immediate response function (GitHub webhook ONLY)
async def send_github_immediate_response(payload: dict, command: WebhookCommand, event_type: str) -> bool:
    """Send immediate response for GitHub webhook ONLY."""
    repo = payload.get("repository", {})
    full_name = repo.get("full_name", "")
    if "/" not in full_name:
        return False
    
    owner, repo_name = full_name.split("/", 1)
    
    # For comments - add reaction
    if "comment" in payload:
        comment_id = payload["comment"].get("id")
        if comment_id:
            try:
                await github_client.add_reaction(owner, repo_name, comment_id, "eyes")
                return True
            except Exception as e:
                logger.warning("github_reaction_failed", error=str(e))
    
    # For issues - post comment
    if "issue" in payload:
        issue_number = payload["issue"].get("number")
        if issue_number:
            try:
                await github_client.post_issue_comment(
                    owner,
                    repo_name,
                    issue_number,
                    f"👀 Processing your `{command.name}` request..."
                )
                return True
            except Exception as e:
                logger.warning("github_comment_failed", error=str(e))
    
    return False


# ✅ Command matching function (GitHub webhook ONLY)
def match_github_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match command for GitHub webhook ONLY. Handles all GitHub event types."""
    text = ""
    if "comment" in payload and "body" in payload["comment"]:
        text = payload["comment"]["body"].lower()
    elif "issue" in payload and "body" in payload["issue"]:
        text = payload["issue"]["body"].lower()
    
    if not text:
        # Use default command
        for cmd in GITHUB_WEBHOOK.commands:
            if cmd.name == GITHUB_WEBHOOK.default_command:
                return cmd
        return GITHUB_WEBHOOK.commands[0] if GITHUB_WEBHOOK.commands else None
    
    # Check prefix
    prefix = GITHUB_WEBHOOK.command_prefix.lower()
    if prefix not in text:
        # Use default command
        for cmd in GITHUB_WEBHOOK.commands:
            if cmd.name == GITHUB_WEBHOOK.default_command:
                return cmd
        return GITHUB_WEBHOOK.commands[0] if GITHUB_WEBHOOK.commands else None
    
    # Find command by name or alias
    for cmd in GITHUB_WEBHOOK.commands:
        if cmd.name.lower() in text:
            return cmd
        for alias in cmd.aliases:
            if alias.lower() in text:
                return cmd
    
    # Fallback to default
    for cmd in GITHUB_WEBHOOK.commands:
        if cmd.name == GITHUB_WEBHOOK.default_command:
            return cmd
    
    return GITHUB_WEBHOOK.commands[0] if GITHUB_WEBHOOK.commands else None


# ✅ Task creation function (GitHub webhook ONLY)
async def create_github_task(
    command: WebhookCommand,
    payload: dict,
    db: AsyncSession
) -> str:
    """Create task for GitHub webhook ONLY. Handles all GitHub event types."""
    # Render template
    message = render_template(command.prompt_template, payload)
    
    # Create task
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    
    # Create session
    webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
    session_db = SessionDB(
        session_id=webhook_session_id,
        user_id="webhook-system",
        machine_id="claude-agent-001",
        connected_at=datetime.utcnow(),
    )
    db.add(session_db)
    
    # Map agent type
    agent_type_map = {
        "planning": AgentType.PLANNING,
        "executor": AgentType.EXECUTOR,
        "brain": AgentType.BRAIN,
    }
    agent_type = agent_type_map.get(command.target_agent, AgentType.PLANNING)
    
    # Create task
    task_db = TaskDB(
        task_id=task_id,
        session_id=webhook_session_id,
        user_id="webhook-system",
        assigned_agent=command.target_agent,
        agent_type=agent_type,
        status=TaskStatus.QUEUED,
        input_message=message,
        source="webhook",
        source_metadata=json.dumps(payload),
    )
    db.add(task_db)
    await db.commit()
    
    return task_id


# ✅ Route handler (GitHub webhook - handles all GitHub events)
@router.post("/github")  # OLD pattern: /webhooks/github (handles issues, PRs, comments)
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Dedicated handler for GitHub webhook.
    Handles all GitHub events: issues, PRs, comments.
    All logic and functions in this file.
    """
    try:
        # Get body for signature verification
        body = await request.body()
        
        # 1. Verify signature
        await verify_github_signature(request, body)
        
        # 2. Parse payload
        payload = json.loads(body.decode())
        payload["provider"] = "github"
        
        # 3. Extract event type (issues.opened, pull_request.opened, issue_comment.created, etc.)
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        action = payload.get("action", "")
        if action:
            event_type = f"{event_type}.{action}"
        
        logger.info("github_webhook_received", event_type=event_type)
        
        # 4. Match command based on event type and payload
        command = match_github_command(payload, event_type)
        if not command:
            return {"status": "received", "actions": 0, "message": "No command matched"}
        
        # 5. Send immediate response
        immediate_response_sent = await send_github_immediate_response(payload, command, event_type)
        
        # 6. Create task
        task_id = await create_github_task(command, payload, db)
        
        # 7. Log event
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        event_db = WebhookEventDB(
            event_id=event_id,
            webhook_id=GITHUB_WEBHOOK.name,  # Use config name
            provider="github",
            event_type=event_type,
            payload_json=json.dumps(payload),
            matched_command=command.name,
            task_id=task_id,
            response_sent=immediate_response_sent,
            created_at=datetime.utcnow()
        )
        db.add(event_db)
        await db.commit()
        
        # 8. Queue task
        await redis_client.push_task(task_id)
        
        logger.info("github_webhook_processed", task_id=task_id, command=command.name, event_type=event_type)
        
        return {
            "status": "processed",
            "event_id": event_id,
            "task_id": task_id,
            "command": command.name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("github_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

**Key Points**:
- ✅ Each provider has its own file (OLD Claude Code CLI pattern)
- ✅ Each file handles all event types for that provider
- ✅ Each file contains route handler + all supporting functions
- ✅ Complete isolation: Everything for one provider in one file
- ✅ NO shared/combo functions
- ✅ Easy to find, modify, add, or remove webhooks
- ✅ Simple endpoints: `/webhooks/github`, `/webhooks/jira`, etc. (matches OLD pattern)

---

## 📝 Key Principles

1. **Explicit over Implicit**: Each provider has its own route and logic
2. **Separation of Concerns**: One provider = one endpoint = one file = one handler = separate functions
3. **File Isolation**: Each provider has its own file with all its functions
4. **Single Responsibility**: Each function handles ONE provider ONLY
5. **No Combo Functions**: NO shared/combo functions that handle multiple providers
6. **Complete Self-Containment**: Everything for one provider in one file
7. **Type Safety**: Pydantic models enforce structure
8. **Developer Friendly**: Easy to add/remove webhooks (just add/delete file)
9. **Clear Intent**: Code clearly shows what each provider webhook does
10. **No Magic**: No generic matching, everything explicit
11. **Function Isolation**: Each provider has its own set of functions (verify, respond, match, create)
12. **Easy Navigation**: Find all code for a provider in one place
13. **OLD Pattern Compliance**: Matches OLD Claude Code CLI pattern exactly

---

## 🚫 What NOT to Do

- ❌ Generic route handler `@router.post("/{provider}")`
- ❌ All webhooks in one file `api/webhooks.py`
- ❌ Combined/combo functions that handle multiple webhook types
- ❌ Shared verification function `verify_webhook_signature(config, ...)` - use separate functions
- ❌ Shared immediate response function `send_immediate_response(config, ...)` - use separate functions
- ❌ Shared command matching function `match_command(config, ...)` - use separate functions
- ❌ Shared task creation function `create_task(config, ...)` - use separate functions
- ❌ Implicit command matching across all webhooks
- ❌ Shared endpoint for multiple webhook types
- ❌ Generic logic that tries to handle everything
- ❌ Database-driven webhook creation
- ❌ Trigger/action system (use name/aliases instead)

---

## ✅ What TO Do

- ✅ **One file per provider**: `api/webhooks/github.py`, `api/webhooks/jira.py`, etc. (OLD pattern)
- ✅ **Each file contains**: Route handler + all supporting functions (verify, respond, match, create)
- ✅ Separate route for each webhook: `@router.post("/github/issues")`
- ✅ Separate handler function for each webhook: `github_issues_webhook()`, `github_pr_webhook()`, etc.
- ✅ Separate verification function for each webhook: `verify_github_issues_signature()`, `verify_github_pr_signature()`, etc.
- ✅ Separate immediate response function for each webhook: `send_github_issues_immediate_response()`, `send_github_pr_immediate_response()`, etc.
- ✅ Separate command matching function for each webhook: `match_github_issues_command()`, `match_github_pr_command()`, etc.
- ✅ Separate task creation function for each webhook: `create_github_issues_task()`, `create_github_pr_task()`, etc.
- ✅ Explicit logic per webhook handler
- ✅ Unique endpoint per webhook config
- ✅ Individual typed variables for configs
- ✅ Hard-coded configurations
- ✅ Name/aliases command matching
- ✅ Immediate response before task queue
- ✅ Each function has single responsibility
- ✅ NO combo/combined functions
- ✅ Complete isolation: One webhook = one file = all its functions
- ✅ **TDD approach**: Write tests first, then implement
- ✅ **Slack notifications**: Send notification after each task completion

---

## 14. ✅ Test-Driven Development (TDD) - Business Logic Focus

**Requirement**: All webhook implementation MUST follow TDD methodology, focusing on **business logic and behavior**, NOT implementation details.

**Key Principle**: Test **WHAT** the system does (behavior), not **HOW** it does it (implementation).

**TDD Process**:
1. **Write tests first** - Before any implementation
2. **Run tests** - Verify they fail (red)
3. **Implement** - Write minimal code to pass tests
4. **Run tests** - Verify they pass (green)
5. **Refactor** - Improve code while keeping tests green

**What to Test (Business Logic)**:
- ✅ **Behavior**: What happens when webhook is received?
- ✅ **Outcomes**: What is the result? What gets created? What gets sent?
- ✅ **Business Rules**: Command matching rules, validation rules, routing rules
- ✅ **User-Facing Behavior**: Immediate responses, notifications, task creation
- ✅ **Error Scenarios**: Invalid signatures, missing data, failures

**What NOT to Test (Implementation Details)**:
- ❌ Specific function names or internal structure
- ❌ Internal variable names or code organization
- ❌ Database query details (test outcomes, not queries)
- ❌ HTTP client implementation details (mock external calls)
- ❌ Internal helper functions (test through public interfaces)

**Test Structure**:
```
tests/
  unit/
    test_webhook_configs.py        # Test config validation (business rules)
    test_webhook_models.py         # Test Pydantic models (data validation)
  
  integration/
    test_webhook_github.py         # Test GitHub webhook behavior
    test_webhook_jira.py           # Test Jira webhook behavior
    test_webhook_slack.py          # Test Slack webhook behavior
    test_webhook_sentry.py         # Test Sentry webhook behavior
```

**Required Tests (Business Logic Focus)**:

### Integration Tests - GitHub Webhook Behavior
```python
# tests/integration/test_webhook_github.py

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

@pytest.mark.integration
@pytest.mark.asyncio
class TestGitHubWebhookBehavior:
    """Test GitHub webhook business logic and behavior."""
    
    async def test_webhook_rejects_invalid_signature(self, client: AsyncClient):
        """
        Business Rule: Webhook must verify signature before processing.
        Behavior: Invalid signature → 401 Unauthorized
        """
        payload = {"issue": {"number": 123, "title": "Test"}}
        headers = {"X-GitHub-Event": "issues", "X-Hub-Signature-256": "invalid"}
        
        response = await client.post(
            "/webhooks/github",
            json=payload,
            headers=headers
        )
        
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()
    
    async def test_webhook_sends_immediate_reaction_on_issue_comment(self, client: AsyncClient):
        """
        Business Rule: User gets immediate feedback when webhook is triggered.
        Behavior: Issue comment with @agent → GitHub reaction sent → Task created
        """
        payload = {
            "action": "created",
            "comment": {"body": "@agent please analyze this"},
            "issue": {"number": 123}
        }
        
        with patch("api.webhooks.github.github_client.post") as mock_github:
            mock_github.return_value = AsyncMock(status_code=200)
            
            response = await client.post(
                "/webhooks/github",
                json=payload,
                headers={"X-GitHub-Event": "issue_comment"}
            )
            
            # Business outcome: Immediate reaction sent
            assert mock_github.called
            assert "reactions" in str(mock_github.call_args)
            
            # Business outcome: Task created
            assert response.status_code == 200
            assert "task_id" in response.json()
    
    async def test_webhook_matches_command_by_name_in_comment(self, client: AsyncClient):
        """
        Business Rule: Commands matched by name or alias in payload text.
        Behavior: Comment contains "analyze" → Matches "analyze" command
        """
        payload = {
            "comment": {"body": "@agent analyze this issue"},
            "issue": {"number": 123}
        }
        
        response = await client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issue_comment"}
        )
        
        # Business outcome: Correct command matched
        assert response.status_code == 200
        task_data = response.json()
        assert task_data["matched_command"] == "analyze"
    
    async def test_webhook_uses_default_command_when_no_match(self, client: AsyncClient):
        """
        Business Rule: Default command used when no specific command matches.
        Behavior: Comment with @agent but no command → Uses default command
        """
        payload = {
            "comment": {"body": "@agent hello"},
            "issue": {"number": 123}
        }
        
        response = await client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issue_comment"}
        )
        
        # Business outcome: Default command used
        assert response.status_code == 200
        task_data = response.json()
        assert task_data["matched_command"] == "default"  # or whatever default is
    
    async def test_webhook_creates_task_with_correct_agent(self, client: AsyncClient):
        """
        Business Rule: Tasks routed to correct agent based on command.
        Behavior: "plan" command → Task created with agent="planning"
        """
        payload = {
            "comment": {"body": "@agent plan the fix"},
            "issue": {"number": 123}
        }
        
        response = await client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issue_comment"}
        )
        
        # Business outcome: Task created with correct agent
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Verify task in database has correct agent
        # (Test outcome, not implementation)
        task_response = await client.get(f"/api/tasks/{task_id}")
        assert task_response.json()["agent"] == "planning"
    
    async def test_webhook_renders_template_with_payload_variables(self, client: AsyncClient):
        """
        Business Rule: Templates rendered with payload variables.
        Behavior: Template "{{issue.title}}" → Rendered with actual issue title
        """
        payload = {
            "comment": {"body": "@agent analyze"},
            "issue": {"number": 123, "title": "Bug in login"}
        }
        
        response = await client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issue_comment"}
        )
        
        # Business outcome: Task message contains rendered template
        task_id = response.json()["task_id"]
        task_response = await client.get(f"/api/tasks/{task_id}")
        task_message = task_response.json()["message"]
        
        assert "Bug in login" in task_message  # Template rendered
    
    async def test_webhook_sends_slack_notification_on_task_completion(self, client: AsyncClient):
        """
        Business Rule: Slack notification sent when task completes.
        Behavior: Task completes → Slack notification sent with task details
        """
        # Create task from webhook
        payload = {
            "comment": {"body": "@agent analyze"},
            "issue": {"number": 123}
        }
        
        webhook_response = await client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issue_comment"}
        )
        task_id = webhook_response.json()["task_id"]
        
        # Simulate task completion
        with patch("httpx.AsyncClient.post") as mock_slack:
            mock_slack.return_value = AsyncMock(status_code=200)
            
            # Trigger task completion (simulate worker processing)
            await client.post(f"/api/tasks/{task_id}/complete", json={"result": "Done"})
            
            # Business outcome: Slack notification sent
            assert mock_slack.called
            slack_payload = mock_slack.call_args[1]["json"]
            assert slack_payload["channel"] == "#ai-agent-activity"
            assert task_id in slack_payload["blocks"][0]["text"]["text"]
```

### Unit Tests - Business Rules and Validation
```python
# tests/unit/test_webhook_configs.py

import pytest
from core.webhook_configs import WEBHOOK_CONFIGS, validate_webhook_configs
from shared.machine_models import WebhookConfig

class TestWebhookConfigValidation:
    """Test webhook configuration business rules."""
    
    def test_all_configs_have_unique_endpoints(self):
        """
        Business Rule: No duplicate endpoints allowed.
        Behavior: Validation fails if endpoints duplicate.
        """
        endpoints = [config.endpoint for config in WEBHOOK_CONFIGS]
        assert len(endpoints) == len(set(endpoints)), "Duplicate endpoints found"
    
    def test_all_configs_have_valid_endpoint_pattern(self):
        """
        Business Rule: Endpoints must match pattern /webhooks/[a-z0-9-]+
        Behavior: Invalid pattern → Validation error
        """
        invalid_config = WebhookConfig(
            name="test",
            endpoint="/invalid/endpoint",  # Invalid pattern
            source="github",
            target_agent="brain",
            commands=[]
        )
        
        with pytest.raises(ValueError, match="endpoint"):
            validate_webhook_configs([invalid_config])
    
    def test_all_commands_have_valid_structure(self):
        """
        Business Rule: Commands must have name, target_agent, prompt_template.
        Behavior: Missing required fields → Validation error
        """
        # Test through config validation
        # (Test business rule, not implementation)
        pass
```

**TDD Workflow (Business Logic Focus)**:
1. **Red**: Write failing test for business behavior
2. **Green**: Implement minimal code to satisfy business requirement
3. **Refactor**: Improve implementation while keeping behavior tests green
4. **Repeat**: For each business requirement

**Test Coverage Requirements (Business Logic)**:
- ✅ **Webhook receives and processes events** (behavior)
- ✅ **Signature verification works** (security requirement)
- ✅ **Immediate responses sent** (user experience requirement)
- ✅ **Commands matched correctly** (business rule)
- ✅ **Tasks created with correct agent** (routing requirement)
- ✅ **Templates rendered correctly** (business rule)
- ✅ **Slack notifications sent** (notification requirement)
- ✅ **Error handling works** (resilience requirement)
- ✅ **Config validation works** (data integrity requirement)

**Testing Principles**:
- ✅ Test **behavior** and **outcomes**, not implementation
- ✅ Test through **public interfaces** (HTTP endpoints, public functions)
- ✅ Use **mocks** for external dependencies (GitHub API, Slack API)
- ✅ Test **business rules** explicitly
- ✅ Test **user-facing behavior** (what user sees/experiences)
- ✅ Avoid testing **internal implementation details**

---

## 15. ✅ Slack Notifications After Task Completion

**Requirement**: Send Slack notification after each task created from a webhook completes (success or failure).

**When to Send**:
- ✅ Task completes successfully
- ✅ Task fails with error
- ✅ Task is cancelled

**Notification Format**:
```python
# Slack notification payload
{
    "channel": "#ai-agent-activity",  # Configurable via env var
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ *Task Completed*\n*Agent:* {{agent_name}}\n*Task:* {{task_title}}\n*Cost:* ${{cost_usd}}\n*Duration:* {{duration}}s"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Source:* {{webhook_source}}\n*Event:* {{event_type}}"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Task ID:* `{{task_id}}`\n*Status:* {{status}}"
                }
            ]
        }
    ]
}
```

**Implementation Requirements**:

### 1. Task Completion Hook
```python
# In task_worker.py or webhook handler

async def send_task_completion_slack_notification(
    task_id: str,
    task_db: TaskDB,
    webhook_source: str,
    event_type: str
) -> None:
    """Send Slack notification when task completes."""
    # Implementation
    pass
```

### 2. Configuration
```python
# Environment variables
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")  # Slack incoming webhook URL
SLACK_NOTIFICATION_CHANNEL = os.getenv("SLACK_NOTIFICATION_CHANNEL", "#ai-agent-activity")
SLACK_NOTIFICATIONS_ENABLED = os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true").lower() == "true"
```

### 3. Integration Points

**Option A: In Task Worker** (Recommended)
```python
# workers/task_worker.py

async def _process_task(self, task_id: str) -> None:
    """Process a task."""
    # ... existing task processing ...
    
    if result.success:
        # ... existing success handling ...
        
        # Send Slack notification if task came from webhook
        if task_db.webhook_source:
            await send_task_completion_slack_notification(
                task_id=task_id,
                task_db=task_db,
                webhook_source=task_db.webhook_source,
                event_type=task_db.webhook_event_type
            )
    else:
        # ... existing failure handling ...
        
        # Send Slack notification for failures too
        if task_db.webhook_source:
            await send_task_completion_slack_notification(
                task_id=task_id,
                task_db=task_db,
                webhook_source=task_db.webhook_source,
                event_type=task_db.webhook_event_type,
                error=result.error
            )
```

**Option B: In Webhook Handler** (Alternative)
```python
# api/webhooks/github.py

async def github_webhook(...):
    """GitHub webhook handler."""
    # ... existing webhook handling ...
    
    # Create task
    task_id = await create_github_task(command, payload, db)
    
    # Store webhook metadata in task for later notification
    task_db.webhook_source = "github"
    task_db.webhook_event_type = event_type
    task_db.webhook_payload = payload
    
    # ... rest of handler ...
```

### 4. Notification Function (Per Provider)
```python
# api/webhooks/github.py

async def send_github_task_completion_notification(
    task_id: str,
    task_db: TaskDB,
    event_type: str,
    success: bool,
    result: Optional[str] = None,
    error: Optional[str] = None
) -> bool:
    """Send Slack notification for GitHub task completion."""
    if not os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true").lower() == "true":
        return False
    
    slack_url = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_url:
        logger.warning("SLACK_WEBHOOK_URL not configured, skipping notification")
        return False
    
    # Build notification message
    status_emoji = "✅" if success else "❌"
    status_text = "Completed" if success else "Failed"
    
    message = {
        "channel": os.getenv("SLACK_NOTIFICATION_CHANNEL", "#ai-agent-activity"),
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{status_emoji} *Task {status_text}*\n*Source:* GitHub ({event_type})\n*Task ID:* `{task_id}`\n*Agent:* {task_db.agent}"
                }
            }
        ]
    }
    
    if success and result:
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Result:*\n```{result[:500]}...```"  # Truncate long results
            }
        })
    
    if error:
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Error:*\n```{error}```"
            }
        })
    
    # Send to Slack
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(slack_url, json=message)
            response.raise_for_status()
            logger.info("slack_notification_sent", task_id=task_id, success=success)
            return True
        except Exception as e:
            logger.error("slack_notification_failed", task_id=task_id, error=str(e))
            return False
```

**Requirements**:
- ✅ Separate notification function per provider (no combo functions)
- ✅ Configurable via environment variables
- ✅ Graceful failure (don't break task processing if Slack fails)
- ✅ Include task metadata (ID, agent, source, event type)
- ✅ Include result/error in notification
- ✅ Support both success and failure notifications
- ✅ Testable (mockable Slack API calls)

**Testing**:
```python
# tests/unit/test_webhook_slack_notifications.py

@pytest.mark.asyncio
async def test_sends_slack_notification_on_task_completion():
    """Test sends Slack notification when task completes."""
    # Write test first
    pass

@pytest.mark.asyncio
async def test_sends_slack_notification_on_task_failure():
    """Test sends Slack notification when task fails."""
    # Write test first
    pass

@pytest.mark.asyncio
async def test_skips_notification_if_disabled():
    """Test skips notification if disabled via env var."""
    # Write test first
    pass
```

---
