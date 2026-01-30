# Dashboard API Container - Claude Configuration

## Component Overview

Log viewer and analytics API for monitoring agent tasks, streaming logs, and system metrics.

## Purpose

- 📊 View task logs in real-time
- 📈 Analytics and metrics dashboards
- 🔍 Search and filter tasks
- 📡 Stream task progress (SSE)
- 📋 Task history and status

## Key Rules

### File Size
- ❌ NO file > 300 lines
- ✅ Split into: routes, models, services, utils

### Type Safety
- ❌ NO `any` types
- ✅ Pydantic `ConfigDict(strict=True)`
- ✅ Explicit types everywhere

### Code Style
- ❌ NO comments in code
- ✅ Self-explanatory names
- ✅ Structured logging: `logger.info("event", key=value)`

## Directory Structure

```
dashboard-api-container/
├── api/
│   ├── routes.py        # FastAPI routes (< 300 lines)
│   ├── models.py        # Pydantic models (< 300 lines)
│   └── dependencies.py  # Dependencies (< 300 lines)
├── services/
│   ├── task_service.py  # Task operations (< 300 lines)
│   ├── log_service.py   # Log reading (< 300 lines)
│   └── stream_service.py # SSE streaming (< 300 lines)
├── tests/
│   ├── test_routes.py
│   ├── test_services.py
│   └── conftest.py
├── Dockerfile
├── pyproject.toml
└── claude.md
```

## Key Operations

### 1. View Task Logs
```python
GET /api/v1/tasks/{task_id}/logs
Response: TaskLogs (all JSONL files)
```

### 2. Stream Task Progress
```python
GET /api/v1/tasks/{task_id}/stream
Response: Server-Sent Events (SSE)
```

### 3. Task History
```python
GET /api/v1/tasks?status=completed&limit=50
Response: List[TaskSummary]
```

### 4. Analytics
```python
GET /api/v1/analytics/summary
Response: SystemMetrics (tasks, success rate, avg duration)
```

## Dependencies

### External Services
- PostgreSQL (task metadata)
- File System (JSONL logs at /data/logs/tasks)
- REST APIs (jira-rest-api, slack-rest-api, sentry-rest-api)

### Environment Variables
```bash
DATABASE_URL=postgresql://...
TASK_LOGS_DIR=/data/logs/tasks
JIRA_REST_API_URL=http://jira-rest-api:8082
SLACK_REST_API_URL=http://slack-rest-api:8083
SENTRY_REST_API_URL=http://sentry-rest-api:8084
```

## Testing

### Requirements
- ✅ Tests run fast (< 5s per file)
- ✅ Mock external dependencies
- ✅ NO real database calls (use in-memory)
- ✅ NO real file system (mock Path operations)

### Example
```python
@pytest.mark.asyncio
async def test_get_task_logs(mock_log_service):
    response = await client.get("/api/v1/tasks/task-123/logs")
    assert response.status_code == 200
    assert "stream" in response.json()
```

## API Routes

### Tasks
- `GET /api/v1/tasks` - List tasks
- `GET /api/v1/tasks/{task_id}` - Get task details
- `GET /api/v1/tasks/{task_id}/logs` - Get all logs
- `GET /api/v1/tasks/{task_id}/stream` - SSE stream

### Analytics
- `GET /api/v1/analytics/summary` - System summary
- `GET /api/v1/analytics/trends` - Time-series data

### Health
- `GET /health` - Health check

## Streaming Logs (SSE)

### Implementation
```python
from fastapi import Response
from sse_starlette.sse import EventSourceResponse

@app.get("/api/v1/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    async def event_generator():
        async for event in log_service.stream_logs(task_id):
            yield {
                "event": event["event_type"],
                "data": json.dumps(event)
            }

    return EventSourceResponse(event_generator())
```

### Client Usage
```javascript
const source = new EventSource('/api/v1/tasks/task-123/stream');
source.addEventListener('progress', (e) => {
    console.log(JSON.parse(e.data));
});
```

## Error Handling

### Custom Exceptions
```python
class TaskNotFoundError(Exception):
    pass

class LogFileNotFoundError(Exception):
    pass
```

### Usage
```python
try:
    task = await task_service.get_task(task_id)
except TaskNotFoundError:
    raise HTTPException(status_code=404, detail="Task not found")
```

## Performance

### Optimizations
- ✅ Connection pooling for PostgreSQL
- ✅ Async file I/O
- ✅ Caching for frequently accessed logs
- ✅ Pagination for large result sets

### Example
```python
@lru_cache(maxsize=100)
async def get_task_summary(task_id: str) -> TaskSummary:
    return await db.get_task(task_id)
```

## Development

### Run Locally
```bash
cd dashboard-api-container
pip install -e ".[dev]"
uvicorn main:app --reload --port 8090
```

### Run Tests
```bash
pytest tests/ -v
```

### Build Docker
```bash
docker build -t dashboard-api .
```

## Integration Points

### Reads From
- PostgreSQL (task metadata)
- File system (JSONL logs)

### Calls
- Jira REST API (optional enrichment)
- Slack REST API (optional enrichment)
- Sentry REST API (optional enrichment)

## Common Patterns

### Reading JSONL Logs
```python
async def read_jsonl(file_path: Path) -> list[dict]:
    events = []
    async with aiofiles.open(file_path, 'r') as f:
        async for line in f:
            events.append(json.loads(line))
    return events
```

### Pagination
```python
@app.get("/api/v1/tasks")
async def list_tasks(
    skip: int = 0,
    limit: int = 50,
    status: TaskStatus | None = None
):
    return await task_service.list_tasks(skip, limit, status)
```

## Monitoring

### Metrics Exposed
- Request count by endpoint
- Response time percentiles
- Error rate
- Active SSE connections

### Health Check
```python
@app.get("/health")
async def health():
    db_ok = await check_database()
    fs_ok = await check_file_system()
    return {
        "status": "healthy" if db_ok and fs_ok else "unhealthy",
        "database": db_ok,
        "file_system": fs_ok
    }
```

## Summary

- 📊 Real-time log viewing and analytics
- 📡 SSE streaming for live progress
- 🔍 Search and filter capabilities
- ⚡ Fast responses (< 100ms for most endpoints)
- 📈 System metrics and trends
- ✅ All files < 300 lines
- ✅ NO `any` types
- ✅ Fast tests (< 5s per file)
