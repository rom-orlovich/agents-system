# On-Error Hook

## Purpose
Handle task failures gracefully, provide diagnostics, and determine retry strategy.

## When Triggered
Automatically runs when an unhandled exception occurs during task execution.

## Execution Order
```
Exception Raised → On-Error Hook → Task Failure Handling
```

## Responsibilities

### 1. Error Classification
- Categorize error type (transient, permanent, user error)
- Determine error severity (critical, high, medium, low)
- Extract stack trace and context
- Identify root cause if possible

### 2. Diagnostics
- Log detailed error information
- Capture system state at failure
- Record execution context
- Generate error report

### 3. Recovery Strategy
- Determine if retry is appropriate
- Calculate backoff delay if retrying
- Decide on partial result handling
- Trigger fallback mechanisms

### 4. Notification
- Post error message to user
- Alert team for critical errors
- Update task status
- Log for monitoring

## Error Classification

### Transient Errors (Retry Appropriate)
```python
TRANSIENT_ERRORS = [
    "ConnectionError",
    "TimeoutError",
    "TemporaryFailure",
    "RateLimitExceeded",
    "ServiceUnavailable"
]
```
**Strategy:** Retry with exponential backoff

### Permanent Errors (No Retry)
```python
PERMANENT_ERRORS = [
    "AuthenticationError",
    "PermissionDenied",
    "ResourceNotFound",
    "InvalidInput",
    "ValidationError"
]
```
**Strategy:** Fail immediately, notify user

### User Errors
```python
USER_ERRORS = [
    "InvalidCommand",
    "MissingRequiredInput",
    "SyntaxError"
]
```
**Strategy:** Provide helpful error message to user

### System Errors
```python
SYSTEM_ERRORS = [
    "OutOfMemory",
    "DiskFull",
    "DatabaseConnectionFailed"
]
```
**Strategy:** Alert ops team, queue for later

## Implementation Flow

```python
async def on_error_hook(
    task_data: dict,
    error: Exception,
    context: dict
) -> HookResult:
    task_id = task_data["task_id"]
    logger = TaskLogger.get_or_create(task_id)

    logger.log_agent_output("error_handling_start", error=str(error))

    error_type = classify_error(error)
    severity = determine_severity(error_type)

    diagnostics = {
        "error_type": error_type,
        "error_message": str(error),
        "stack_trace": traceback.format_exc(),
        "severity": severity,
        "task_state": capture_state(context)
    }

    logger.log_agent_output("error_diagnostics", **diagnostics)

    recovery = determine_recovery_strategy(error_type)

    if recovery.should_retry:
        return HookResult(
            success=False,
            retry=True,
            retry_after_seconds=recovery.backoff_seconds,
            error_info=diagnostics
        )

    await notify_error(task_data, diagnostics, recovery)

    logger.log_agent_output("error_handling_complete")

    return HookResult(
        success=False,
        retry=False,
        error_info=diagnostics
    )
```

## Retry Strategy

### Exponential Backoff
```python
def calculate_backoff(attempt: int) -> int:
    base_delay = 2  # seconds
    max_delay = 300  # 5 minutes
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter
```

### Max Retry Attempts
- Transient errors: 3 attempts
- Rate limits: 5 attempts
- Other: 1 attempt (no retry)

## User Notification Format

### For User Errors
```markdown
## Error in Task Execution ❌

I encountered an error while processing your request:

**Error:** Invalid command syntax

**Details:** The command `@agent reviw` was not recognized. Did you mean `@agent review`?

**Suggestion:** Please check the command and try again.

Available commands:
- `@agent review`: Code review
- `@agent test`: Generate tests
- `@agent explain`: Explain code
- `@agent fix`: Fix bugs

Need help? See [documentation](#).
```

### For System Errors
```markdown
## Temporary Issue ⚠️

I encountered a temporary issue while processing your request. I'll automatically retry in a moment.

**Error:** Connection timeout
**Retry:** Attempting again in 4 seconds (attempt 2/3)

No action needed from you.
```

### For Permanent Errors
```markdown
## Unable to Complete Task ❌

I was unable to complete your request due to:

**Error:** Repository not found (404)

**Possible causes:**
- Repository name incorrect
- Repository is private and I don't have access
- Repository was deleted

**Next steps:**
1. Verify the repository exists
2. Check my access permissions
3. Try again or contact support

Task ID: task-abc-123 (for reference)
```

## Diagnostics Captured

### System State
```python
{
  "memory_available_mb": 128,
  "disk_free_gb": 5.2,
  "active_connections": 3,
  "queue_length": 12
}
```

### Execution Context
```python
{
  "task_id": "task-abc-123",
  "current_step": "result_posting",
  "elapsed_seconds": 23.4,
  "partial_result": "..."
}
```

### Error Details
```python
{
  "exception_type": "ConnectionError",
  "exception_message": "Connection refused",
  "file": "core/mcp_client.py",
  "line": 45,
  "function": "call_tool"
}
```

## Severity Levels

### Critical
- Data loss risk
- Security breach
- System crash
**Action:** Page on-call, halt system

### High
- Task failure impacting users
- Service degradation
**Action:** Alert team, log for analysis

### Medium
- Recoverable errors
- Expected failures (rate limits)
**Action:** Log and retry

### Low
- User input errors
- Non-critical warnings
**Action:** Log and inform user

## Output Format

```json
{
  "hook": "on-error",
  "task_id": "task-abc-123",
  "error_classified": true,
  "error_type": "transient",
  "severity": "medium",
  "retry": true,
  "retry_after_seconds": 4,
  "user_notified": true,
  "diagnostics_saved": true
}
```

## Integration Points
- **Task Worker:** Calls on exception
- **Result Poster:** Notifies user of error
- **Monitoring:** Sends alerts
- **Analytics:** Tracks error rates
