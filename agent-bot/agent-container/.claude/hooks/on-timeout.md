# On-Timeout Hook

## Purpose
Handle task timeouts gracefully, preserve work done, and provide feedback to users.

## When Triggered
Automatically runs when task execution exceeds maximum allowed duration.

## Execution Order
```
Timeout Detected → On-Timeout Hook → Task Cancellation
```

## Timeout Thresholds
- **Default task:** 10 minutes
- **Code review:** 5 minutes
- **Test generation:** 5 minutes
- **Bug fix:** 10 minutes
- **Refactoring:** 15 minutes
- **Explanation:** 2 minutes

## Responsibilities

### 1. Graceful Shutdown
- Signal running processes to stop
- Save partial results
- Close open resources
- Terminate CLI execution

### 2. State Preservation
- Save work completed so far
- Log progress achieved
- Store partial analysis
- Mark checkpoint for potential resume

### 3. User Notification
- Inform user of timeout
- Explain what was completed
- Suggest how to proceed
- Offer to retry with scope reduction

### 4. Diagnostics
- Log timeout reason
- Identify bottleneck
- Record resource usage
- Suggest optimizations

## Implementation Flow

```python
async def on_timeout_hook(
    task_data: dict,
    elapsed_seconds: float,
    partial_result: PartialResult | None,
    context: dict
) -> HookResult:
    task_id = task_data["task_id"]
    logger = TaskLogger.get_or_create(task_id)

    logger.log_agent_output(
        "timeout_detected",
        elapsed=elapsed_seconds,
        threshold=get_timeout_threshold(task_data)
    )

    await signal_graceful_shutdown(context.get("cli_process"))

    if partial_result:
        await save_partial_result(task_id, partial_result)

    diagnostics = analyze_timeout(task_data, context, elapsed_seconds)

    await notify_user_of_timeout(task_data, diagnostics, partial_result)

    await cleanup_resources(context)

    logger.log_agent_output("timeout_handled", **diagnostics)

    return HookResult(
        success=False,
        timeout=True,
        partial_result=partial_result,
        diagnostics=diagnostics
    )
```

## Timeout Analysis

### Identify Bottleneck
```python
def analyze_timeout(task_data, context, elapsed):
    if elapsed < 60:
        bottleneck = "initialization"
    elif "cli_start_time" not in context:
        bottleneck = "pre_execution"
    elif elapsed - context["cli_start_time"] > threshold * 0.8:
        bottleneck = "cli_execution"
    else:
        bottleneck = "result_posting"

    return {
        "bottleneck": bottleneck,
        "suggestion": get_suggestion(bottleneck),
        "elapsed": elapsed
    }
```

### Suggestions by Bottleneck
- **initialization:** "Repository too large, try --shallow-clone"
- **pre_execution:** "Graph indexing slow, skip with --no-index"
- **cli_execution:** "Request too complex, narrow scope or break into sub-tasks"
- **result_posting:** "Result too large, summarize before posting"

## User Notification Format

### With Partial Result
```markdown
## Task Timeout ⏱️

Your request took longer than expected and was stopped after 10 minutes.

**What I completed:**
✅ Analyzed 12 of 15 files
✅ Found 3 security issues
⏸️ In progress: Test coverage analysis

**Partial results:**
### Security Issues Found
1. **SQL Injection Risk** in `api/routes.py:45`
2. **Missing Input Validation** in `core/processor.py:23`
3. **Hardcoded Secret** in `config/settings.py:12`

**To get complete results:**
- Option 1: Retry with fewer files: `@agent review --files "api/*.py"`
- Option 2: Break into smaller tasks
- Option 3: Increase timeout (contact admin)

**Bottleneck:** CLI execution (complex analysis)
**Suggestion:** Try reviewing individual modules separately

Task ID: task-abc-123
```

### Without Partial Result
```markdown
## Task Timeout ⏱️

Your request exceeded the 10-minute time limit.

**Progress:**
- ✅ Repository cloned
- ✅ Code indexed
- ⏸️ Stopped during: Analysis phase

**What happened:**
The codebase is large (5000+ files) and analysis is taking longer than expected.

**Recommended actions:**
1. **Narrow scope:** Specify which files/modules to analyze
   - `@agent review --files "src/core/*.py"`
2. **Break into parts:** Review components separately
   - `@agent review api-gateway`
   - `@agent review agent-container`
3. **Skip indexing:** Faster but limited context
   - `@agent review --no-index`

**Example:**
`@agent review --files "src/*.py" --focus security`

Need help? See [optimization guide](#).

Task ID: task-abc-123
```

## Partial Result Handling

### Save Partial Work
```python
partial_result = {
    "task_id": task_id,
    "progress_pct": 75,
    "completed_steps": ["clone", "index", "parse", "analyze_security"],
    "pending_steps": ["analyze_performance", "generate_report"],
    "data": {
        "security_issues": [...],
        "files_analyzed": 12,
        "total_files": 15
    }
}
```

### Resume Capability (Future)
```python
{
  "resumable": true,
  "checkpoint_id": "chk-abc-123",
  "resume_from": "analyze_performance",
  "expires_at": "2024-01-20T15:00:00Z"
}
```

## Graceful Shutdown

### Shutdown Sequence
1. Set shutdown flag
2. Send SIGTERM to child processes
3. Wait up to 5 seconds for cleanup
4. Send SIGKILL if still running
5. Close all file handles
6. Flush logs
7. Save state

### Preserve State
```python
state = {
    "current_phase": "analysis",
    "files_processed": ["file1.py", "file2.py"],
    "intermediate_results": {...},
    "next_file": "file3.py"
}
```

## Output Format

```json
{
  "hook": "on-timeout",
  "task_id": "task-abc-123",
  "elapsed_seconds": 602,
  "threshold_seconds": 600,
  "bottleneck": "cli_execution",
  "partial_result_saved": true,
  "user_notified": true,
  "shutdown_graceful": true,
  "suggestion": "Narrow scope or break into smaller tasks"
}
```

## Monitoring & Alerts

### Track Timeout Rates
- Overall timeout rate target: < 5%
- By task type timeout rates
- Bottleneck distribution
- Average timeout recovery time

### Alert Conditions
- Timeout rate > 10%: Alert team
- Specific bottleneck > 50%: Investigate optimization
- Frequent timeouts for same repo: Flag for review

## Performance Optimization

### Preemptive Actions
- Warn at 80% of timeout threshold
- Offer to skip non-critical steps
- Suggest scope reduction proactively

### Timeout Prevention
- Estimate task duration before starting
- Reject overly complex requests upfront
- Provide scoping guidance
- Cache expensive operations

## Integration Points
- **Task Worker:** Monitors elapsed time
- **CLI Runner:** Responds to shutdown signals
- **Result Poster:** Posts timeout notification
- **Analytics:** Tracks timeout patterns
