# Post-Execution Hook

## Purpose
Finalize task execution, clean up resources, and ensure results are properly stored and delivered.

## When Triggered
Automatically runs after task processing completes, whether successful or failed.

## Execution Order
```
Task Processing → Post-Execution Hook → Task Complete
```

## Responsibilities

### 1. Result Verification
- Verify result was generated
- Validate result format
- Check result delivery status
- Ensure logs are complete

### 2. Cleanup
- Close open file handles
- Release memory buffers
- Clean temporary files
- Close streaming logger

### 3. Metrics Collection
- Record execution duration
- Log resource usage
- Track success/failure rate
- Update analytics

### 4. Notification
- Confirm result delivery
- Update task status in database
- Trigger any follow-up actions
- Send notifications if configured

## Implementation Flow

```python
async def post_execution_hook(
    task_data: dict,
    result: TaskResult,
    context: dict
) -> HookResult:
    task_id = task_data["task_id"]
    logger = TaskLogger.get_or_create(task_id)

    logger.log_agent_output("post_execution_start")

    try:
        await verify_result_delivery(task_id, result)

        await cleanup_task_resources(task_id, context)

        metrics = await collect_metrics(task_id, result)

        await update_task_status(task_id, result.success)

        await cleanup_old_tasks()

        logger.log_agent_output(
            "post_execution_complete",
            success=result.success,
            metrics=metrics
        )

        return HookResult(success=True, metrics=metrics)

    except Exception as e:
        logger.log_agent_output("post_execution_error", error=str(e))
        return HookResult(success=False, error=str(e))
```

## Cleanup Actions

### Temporary Files
```python
cleanup_patterns = [
    f"/tmp/task-{task_id}-*",
    f"/app/tmp/{task_id}/*",
    "*.pyc",
    "__pycache__"
]
```

### Resource Release
- Close streaming logger
- Close MCP client connections
- Release file locks
- Clear memory caches

### Old Task Cleanup
- Remove task logs older than 7 days
- Delete temporary repositories not accessed in 24 hours
- Clean up failed task artifacts

## Metrics Collected

### Execution Metrics
```python
{
  "duration_seconds": 45.2,
  "tokens_used": {
    "input": 1234,
    "output": 567,
    "total": 1801
  },
  "cost_usd": 0.123,
  "model": "claude-3-opus"
}
```

### Resource Metrics
```python
{
  "memory_peak_mb": 256,
  "disk_used_mb": 120,
  "api_calls": 3,
  "files_processed": 12
}
```

### Quality Metrics
```python
{
  "success": true,
  "error_type": null,
  "retry_count": 0,
  "result_delivered": true
}
```

## Output Format

### Success
```json
{
  "hook": "post-execution",
  "task_id": "task-abc-123",
  "status": "complete",
  "result_delivered": true,
  "cleanup_complete": true,
  "metrics": {
    "duration_seconds": 45.2,
    "cost_usd": 0.123,
    "success": true
  }
}
```

### Partial Failure
```json
{
  "hook": "post-execution",
  "task_id": "task-abc-123",
  "status": "partial",
  "result_delivered": false,
  "cleanup_complete": true,
  "warnings": ["Result delivery failed but logged"]
}
```

## Follow-up Actions

### On Success
- Mark task complete in database
- Archive task logs
- Update analytics dashboard
- Clear task from active queue

### On Failure
- Keep task logs for debugging
- Update failure metrics
- Optionally retry based on error type
- Notify on critical failures

## Performance Targets
- Hook execution: < 2s
- Cleanup: < 1s
- Metrics collection: < 500ms
- Database update: < 500ms

## Logging Events
```python
logger.log_agent_output("post_execution_start")
logger.log_agent_output("verifying_result_delivery")
logger.log_agent_output("cleaning_resources")
logger.log_agent_output("collecting_metrics")
logger.log_agent_output("post_execution_complete")
```
