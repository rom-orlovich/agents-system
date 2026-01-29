# Task Logging System

## Overview

The task logging system provides structured, comprehensive logging for every task executed through webhooks or the dashboard. Logs are stored in a dedicated directory per task with timestamped JSONL streams and static JSON metadata.

## Log Structure

Each task creates a directory at `/data/logs/tasks/{task_id}/` containing:

```
{task_id}/
├── metadata.json              # Task metadata (static)
├── 01-input.json              # Task input (static)
├── 02-webhook-flow.jsonl      # Webhook events stream
├── 03-agent-output.jsonl      # Agent output stream (thinking, tool calls, messages)
└── 04-final-result.json       # Final result and metrics (static)
```

## File Formats

### metadata.json

Task metadata including source, provider, assigned agent, and model.

```json
{
  "task_id": "task-abc123def456",
  "source": "webhook",
  "provider": "github",
  "created_at": "2026-01-29T13:00:00.000000Z",
  "started_at": "2026-01-29T13:00:05.000000Z",
  "status": "running",
  "assigned_agent": "planning",
  "agent_type": "AgentType.PLANNING",
  "model": "claude-sonnet-4-5-20250929"
}
```

### 01-input.json

Original task input with source metadata.

```json
{
  "message": "@agent analyze this issue",
  "source_metadata": {
    "provider": "github",
    "event_type": "issue_comment.created",
    "repo": "user/repo",
    "issue_number": 42,
    "command": "analyze"
  }
}
```

### 02-webhook-flow.jsonl

Webhook processing stages (JSONL format - one JSON object per line).

```jsonl
{"timestamp": "2026-01-29T13:00:00.100000Z", "stage": "received", "event_type": "issue_comment.created", "repo": "user/repo"}
{"timestamp": "2026-01-29T13:00:00.200000Z", "stage": "validation", "status": "passed"}
{"timestamp": "2026-01-29T13:00:00.300000Z", "stage": "command_matching", "command": "analyze", "matched": true}
{"timestamp": "2026-01-29T13:00:00.400000Z", "stage": "immediate_response", "success": true}
{"timestamp": "2026-01-29T13:00:00.500000Z", "stage": "task_created", "task_id": "task-abc123def456", "agent": "planning"}
{"timestamp": "2026-01-29T13:00:00.600000Z", "stage": "queue_push", "status": "queued"}
```

### 03-agent-output.jsonl

Agent output stream including thinking, tool calls, and messages (JSONL format).

```jsonl
{"timestamp": "2026-01-29T13:00:05.100000Z", "type": "output", "content": "<thinking>Analyzing the issue...</thinking>"}
{"timestamp": "2026-01-29T13:00:05.500000Z", "type": "output", "content": "Reading file..."}
{"timestamp": "2026-01-29T13:00:06.000000Z", "type": "output", "content": "Analysis complete"}
```

### 04-final-result.json

Final task result with success status, output, and metrics.

```json
{
  "success": true,
  "result": "Analysis complete. Found 3 issues...",
  "error": null,
  "metrics": {
    "cost_usd": 0.05,
    "input_tokens": 1000,
    "output_tokens": 500,
    "duration_seconds": 45.2
  },
  "completed_at": "2026-01-29T13:01:00.000000Z"
}
```

## Configuration

Logging is controlled via `core/config.py`:

```python
task_logs_enabled: bool = True
task_logs_dir: Path = Path("/data/logs/tasks")
task_logs_retention_days: int = 30
```

## Implementation

### Webhook Integration

All webhooks (GitHub, Jira, Slack) use TaskLogger:

1. Generate task_id early
2. Initialize TaskLogger
3. Log webhook stages: received → validation → command_matching → immediate_response → task_created → queue_push
4. Write metadata and input files

### Task Worker Integration

The task worker logs agent outputs and final results:

1. Initialize TaskLogger from task_id
2. Stream agent output chunks to `03-agent-output.jsonl`
3. Write final result to `04-final-result.json` on completion/failure

### Error Handling

All logging operations are non-blocking - failures are logged as warnings but don't stop task execution.

## Usage

### Viewing Logs

```bash
# List all task logs
ls -la /data/logs/tasks/

# View specific task
cat /data/logs/tasks/task-abc123def456/metadata.json
cat /data/logs/tasks/task-abc123def456/02-webhook-flow.jsonl

# Stream agent output
tail -f /data/logs/tasks/task-abc123def456/03-agent-output.jsonl
```

### Querying JSONL Files

```bash
# Extract specific fields using jq
cat 02-webhook-flow.jsonl | jq -r '.stage'

# Filter by stage
cat 02-webhook-flow.jsonl | jq 'select(.stage == "validation")'

# Get timestamps
cat 03-agent-output.jsonl | jq -r '.timestamp'
```

## Thread Safety

- JSON files use atomic write operations (temp file + rename)
- JSONL appends use atomic append mode (safe for concurrent writes on POSIX systems)

## Future Enhancements

- Automatic log cleanup based on `task_logs_retention_days`
- Centralized logging system integration
- Log compression for long-term storage
- API endpoints for querying logs
