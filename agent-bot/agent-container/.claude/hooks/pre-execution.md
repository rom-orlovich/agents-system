# Pre-Execution Hook

## Purpose
Prepare environment and validate preconditions before task execution begins.

## When Triggered
Automatically runs before every task execution, after task is dequeued from Redis but before any processing logic.

## Execution Order
```
Task dequeued → Pre-Execution Hook → Task Processing → Post-Execution Hook
```

## Responsibilities

### 1. Validation
- Verify task has all required inputs
- Validate task_id format
- Check organization installation is active
- Ensure required skills/agents are available
- Verify sufficient system resources

### 2. Environment Setup
- Create working directory for task
- Set up isolated environment variables
- Initialize logging infrastructure
- Configure MCP client connections

### 3. Repository Management
- Clone repository if not cached
- Update repository to latest commit
- Checkout specific ref/PR if specified
- Verify repository access permissions

### 4. Knowledge Graph Indexing
- Check if repository is indexed
- Index repository if needed or stale
- Update graph with latest code changes
- Verify graph query availability

### 5. Context Loading
- Load organization settings
- Fetch installation credentials
- Load repository metadata
- Initialize task logger

## Implementation Flow

```python
async def pre_execution_hook(task_data: dict) -> HookResult:
    task_id = task_data["task_id"]
    logger = TaskLogger.get_or_create(task_id)

    logger.log_webhook_event("pre_execution_start")

    try:
        validate_task_inputs(task_data)

        installation = await load_installation(task_data["installation_id"])

        if not installation.is_active:
            return HookResult(
                success=False,
                skip_task=True,
                reason="Installation inactive"
            )

        repo_path = await ensure_repository(
            installation_id=installation.id,
            repo=task_data["metadata"]["repository"],
            ref=task_data["metadata"].get("ref", "main")
        )

        if task_data["metadata"].get("pr_number"):
            await checkout_pr(repo_path, task_data["metadata"]["pr_number"])

        await index_repository(repo_path)

        context = {
            "repo_path": str(repo_path),
            "installation": installation,
            "graph_indexed": True
        }

        logger.log_webhook_event("pre_execution_complete", **context)

        return HookResult(
            success=True,
            context=context
        )

    except Exception as e:
        logger.log_webhook_event("pre_execution_failed", error=str(e))
        return HookResult(
            success=False,
            error=str(e)
        )
```

## Validation Checks

### Required Fields
```python
REQUIRED_FIELDS = [
    "task_id",
    "installation_id",
    "input_message",
    "metadata.repository"
]
```

### Resource Checks
```python
- Disk space > 1GB free
- Memory > 512MB available
- Redis connection healthy
- Database connection healthy
```

### Installation Checks
```python
- Installation exists
- Installation.is_active == True
- Access token not expired
- Required scopes granted
```

## Output Format

### Success
```json
{
  "hook": "pre-execution",
  "task_id": "task-abc-123",
  "status": "ready",
  "duration_ms": 2340,
  "context": {
    "repo_path": "/data/repos/org-123/owner_repo",
    "installation_id": "inst-456",
    "graph_indexed": true,
    "files_count": 1234,
    "pr_checked_out": true,
    "pr_number": 789
  }
}
```

### Failure
```json
{
  "hook": "pre-execution",
  "task_id": "task-abc-123",
  "status": "failed",
  "error": "Repository not accessible: 404 Not Found",
  "skip_task": true
}
```

### Skip Task
```json
{
  "hook": "pre-execution",
  "task_id": "task-abc-123",
  "status": "skipped",
  "reason": "Installation inactive",
  "skip_task": true
}
```

## Failure Handling

### Missing Inputs
- **Action:** Return error with specific missing fields
- **Task Outcome:** Skip task, log error
- **User Notification:** Post error message to source

### Inactive Installation
- **Action:** Skip task silently
- **Task Outcome:** Log and skip
- **User Notification:** None (installation was uninstalled)

### Repository Inaccessible
- **Action:** Retry with exponential backoff (3 attempts)
- **Task Outcome:** Skip if still failing after retries
- **User Notification:** Post error about access issues

### Resource Shortage
- **Action:** Queue task for later retry
- **Task Outcome:** Re-queue with delay
- **User Notification:** None (will retry automatically)

### Indexing Failure
- **Action:** Proceed without graph (degraded mode)
- **Task Outcome:** Continue but log warning
- **User Notification:** Warn that some features unavailable

## Performance Targets
- Cached repository: < 500ms
- New repository clone: < 10s
- Graph indexing: < 5s
- Total hook time: < 15s

## Caching Strategy
- Repository cache TTL: 24 hours
- Graph index cache: Until repo update
- Installation data: Cache per session
- Metadata cache: 1 hour

## Logging Events
```python
logger.log_webhook_event("pre_execution_start")
logger.log_webhook_event("validating_inputs")
logger.log_webhook_event("loading_installation")
logger.log_webhook_event("ensuring_repository")
logger.log_webhook_event("indexing_graph")
logger.log_webhook_event("pre_execution_complete")
```

## Integration Points
- **Task Worker:** Calls hook before process_task()
- **Repo Manager:** Uses to clone/update repos
- **Graph Indexer:** Uses to index code
- **Token Service:** Uses to fetch credentials
