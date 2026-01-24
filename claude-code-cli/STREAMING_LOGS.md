# Streaming Logs Feature

## Overview

The webhook-triggered Claude CLI tasks now support **real-time streaming logs** that are stored in Redis and accessible via REST API. This provides live visibility into task execution progress.

## What Changed

### Before
- Claude CLI output was captured using `process.communicate()` which blocks until completion
- No visibility into task progress during execution
- Bad UX - users had to wait without knowing if the task was processing

### After
- Claude CLI output is streamed line-by-line to Redis as it happens
- Real-time logs accessible via API endpoint
- Each log entry includes timestamp and message
- Logs stored for 24 hours

## Architecture

### 1. Worker Streaming (planning-agent/worker.py)

The `_run_claude_code` method now:
1. Creates subprocess with stdout/stderr pipes
2. Reads output line-by-line asynchronously
3. Stores each line to Redis with `queue.append_task_log(task_id, log_line)`
4. Logs are prefixed with `[stdout]` or `[stderr]`

```python
async def read_stream(stream, is_stderr=False):
    """Read stream line by line and log to Redis."""
    while True:
        line = await stream.readline()
        if not line:
            break

        decoded_line = line.decode("utf-8").rstrip()
        await self.queue.append_task_log(task_id, f"[{log_type}] {decoded_line}")
```

### 2. Redis Storage (task_queue.py)

New methods added:
- `append_task_log(task_id, log_line)` - Append log entry with timestamp
- `get_task_logs(task_id, offset, limit)` - Retrieve logs with pagination

Logs are stored as:
- **Key**: `tasks:{task_id}:logs` (Redis list)
- **Format**: JSON `{"timestamp": "2026-01-24T...", "message": "[stdout] ..."}`
- **Expiration**: 24 hours

### 3. API Endpoints (routes/tasks.py)

New REST endpoints for task management:

#### GET /tasks/{task_id}/logs
Fetch streaming logs for a task

**Query Parameters:**
- `offset` (int, default=0): Starting log index
- `limit` (int, default=100): Number of logs (-1 for all)
- `follow` (bool, default=false): Reserved for future WebSocket streaming

**Response:**
```json
{
  "task_id": "task-1737737400.123",
  "logs": [
    {
      "timestamp": "2026-01-24T10:00:00.000Z",
      "message": "[stdout] Claude Code CLI process started"
    },
    {
      "timestamp": "2026-01-24T10:00:01.500Z",
      "message": "[stdout] Reading repository..."
    }
  ],
  "offset": 0,
  "limit": 100,
  "total": 45,
  "has_more": false
}
```

#### GET /tasks/{task_id}/status
Get current task status

**Response:**
```json
{
  "task_id": "task-1737737400.123",
  "status": "discovering",
  "metadata": {
    "status": "discovering",
    "updated_at": "2026-01-24T10:00:00Z",
    "plan": "...",
    "queue": "planning-queue"
  }
}
```

#### GET /tasks/{task_id}
Get complete task details

#### GET /tasks/
List all tasks with optional status filter

**Query Parameters:**
- `status` (string, optional): Filter by status (queued, discovering, pending_approval, approved, executing, completed, failed)
- `limit` (int, default=50): Max tasks to return

## Testing

### 1. Trigger a Task via Webhook

Send a Sentry or Jira webhook to trigger a task:

```bash
# Sentry webhook example
curl -X POST http://localhost:8000/webhooks/sentry \
  -H "Content-Type: application/json" \
  -d '{
    "id": "123",
    "data": {
      "event": {
        "message": "TypeError in payment service",
        "tags": [
          ["repository", "myorg/myrepo"]
        ]
      }
    }
  }'
```

This will return a `task_id`.

### 2. Poll Logs in Real-Time

While the task is running, poll for logs:

```bash
# Get latest logs
curl http://localhost:8000/tasks/task-1737737400.123/logs?limit=100

# Get next batch (offset by previous count)
curl http://localhost:8000/tasks/task-1737737400.123/logs?offset=100&limit=100

# Get all logs
curl http://localhost:8000/tasks/task-1737737400.123/logs?limit=-1
```

### 3. Check Task Status

```bash
curl http://localhost:8000/tasks/task-1737737400.123/status
```

### 4. UI Integration Example

```javascript
// Poll logs every 2 seconds
async function pollLogs(taskId) {
  let offset = 0;
  const interval = setInterval(async () => {
    const response = await fetch(`/tasks/${taskId}/logs?offset=${offset}&limit=50`);
    const data = await response.json();

    // Display new logs
    data.logs.forEach(log => {
      console.log(`[${log.timestamp}] ${log.message}`);
      appendToUI(log);
    });

    offset += data.logs.length;

    // Stop polling if task completed
    const statusResponse = await fetch(`/tasks/${taskId}/status`);
    const statusData = await statusResponse.json();
    if (['completed', 'failed'].includes(statusData.status)) {
      clearInterval(interval);
    }
  }, 2000);
}
```

### 5. Testing with Local Claude CLI

Compare local terminal output vs webhook output:

```bash
# Local terminal (you'll see streaming output)
cd /workspace/task-test
claude -p --output-format json "Fix the bug"

# Webhook-triggered (logs streamed to Redis)
# Trigger via webhook, then:
curl http://localhost:8000/tasks/{task_id}/logs
```

## Logs You'll See

Example log messages during execution:

```
[stdout] Claude Code CLI process started, PID: 12345
[stdout] Reading repository structure...
[stdout] Analyzing error trace from Sentry...
[stdout] Creating fix plan...
[stdout] Writing test file: tests/test_payment.py
[stdout] Running tests...
[stderr] Warning: Deprecated API usage
[stdout] Tests passed: 5/5
[stdout] Creating pull request...
[stdout] PR created: https://github.com/org/repo/pull/42
```

## Future Enhancements

1. **WebSocket Support**: Real-time push instead of polling
2. **Log Filtering**: Filter by log level or keyword
3. **Log Search**: Full-text search across task logs
4. **Progress Indicators**: Parse structured progress updates from Claude CLI
5. **Slack Integration**: Send log snippets to Slack during execution

## Troubleshooting

### No logs appearing?
1. Check Redis connection: `redis-cli ping`
2. Verify worker is running: `docker ps | grep planning-agent`
3. Check worker logs: `docker logs planning-agent-worker`

### Logs cut off?
- Default timeout is 300s (5 min) for planning agent
- Increase in `shared/config.py`: `PLANNING_AGENT_TIMEOUT`

### Old logs not visible?
- Logs expire after 24 hours
- Adjust expiration in `task_queue.py`: `await self.redis.expire(f"tasks:{task_id}:logs", 86400)`

## Files Modified

1. `shared/task_queue.py` - Added `append_task_log()` and `get_task_logs()`
2. `agents/planning-agent/worker.py` - Stream stdout/stderr line-by-line
3. `services/webhook-server/routes/tasks.py` - New API endpoints (NEW FILE)
4. `services/webhook-server/main.py` - Register tasks router

## API Documentation

Full API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
