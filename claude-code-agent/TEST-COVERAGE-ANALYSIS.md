# Test Coverage Analysis - What Can Break

## Summary
- **Production Code**: 2,174 lines
- **Test Code**: 344 lines
- **Test Coverage**: ~15% by lines
- **Unit Tests**: ✅ 11/11 passing (Pydantic models only)
- **Integration Tests**: ❌ 5/7 failing
- **E2E Tests**: ❌ 0 tests (directory exists but empty)

---

## ✅ What IS Tested (Well Covered)

### Pydantic Models (`shared/machine_models.py`)
All business rule validations are tested:

1. **Task Model** (lines 120-186)
   - ✅ Status transitions (QUEUED → RUNNING → COMPLETED)
   - ✅ Invalid transition rejection
   - ✅ Automatic timing updates (started_at, completed_at, duration)
   - ✅ Validation rules

2. **Session Model** (lines 80-114)
   - ✅ Task tracking (no duplicates)
   - ✅ Cost accumulation
   - ✅ Validation

3. **Other Models**
   - ✅ MachineConfig validation
   - ✅ ClaudeCredentials expiry logic
   - ✅ WebhookConfig name validation

---

## ❌ What is NOT Tested (Critical Gaps)

### 1. CLI Runner (`core/cli_runner.py`) - 158 lines, 0 tests

**What can break**:
```python
# Line 60-69: Subprocess spawning
process = await asyncio.create_subprocess_exec(
    *cmd,
    cwd=str(working_dir),
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env={**os.environ, "CLAUDE_TASK_ID": task_id}
)
```

**Risks**:
- ❌ Claude CLI not installed → subprocess fails
- ❌ Working directory doesn't exist → process crashes
- ❌ Invalid prompt → CLI returns error
- ❌ Timeout handling not tested
- ❌ JSON parsing errors not tested
- ❌ Process zombie if output queue is full

**Impact**: 🔴 HIGH - This is the core execution engine

---

### 2. Task Worker (`workers/task_worker.py`) - 180 lines, 0 tests

**What can break**:
```python
# Line 33: Queue popping
task_id = await redis_client.pop_task(timeout=5)

# Line 79-87: CLI spawning
cli_task = asyncio.create_task(
    run_claude_cli(
        prompt=task_db.input_message,
        working_dir=agent_dir,
        output_queue=output_queue,
        task_id=task_id,
        timeout_seconds=settings.task_timeout_seconds,
    )
)

# Line 99-103: WebSocket streaming
await self.ws_hub.send_to_session(
    task_db.session_id,
    TaskOutputMessage(task_id=task_id, chunk=chunk)
)
```

**Risks**:
- ❌ Redis connection lost → worker stops processing
- ❌ Database transaction fails → task stuck in RUNNING state
- ❌ WebSocket disconnected → output lost
- ❌ Multiple workers race condition → same task processed twice
- ❌ Output queue overflow → memory leak
- ❌ Task cancellation not tested

**Impact**: 🔴 HIGH - This is the main processing loop

---

### 3. Redis Client (`core/database/redis_client.py`) - Not shown but critical

**What can break**:
```python
# Connection handling
await redis_client.connect()
await redis_client.disconnect()

# Queue operations
await redis_client.push_task(task_id)
task_id = await redis_client.pop_task(timeout=5)
await redis_client.queue_length()
```

**Risks**:
- ❌ Redis server down → all operations fail
- ❌ Network timeout → tasks stuck
- ❌ Connection pool exhausted → deadlock
- ❌ No retry logic → single failure stops system

**Impact**: 🔴 CRITICAL - Without Redis, nothing works

---

### 4. WebSocket Hub (`core/websocket_hub.py`) - Not shown, 0 tests

**What can break**:
```python
# Connection management
register_connection(session_id, websocket)
unregister_connection(session_id, websocket)
send_to_session(session_id, message)
```

**Risks**:
- ❌ Client disconnects → stale connections in memory leak
- ❌ Concurrent broadcasts → race condition
- ❌ Message serialization fails → exception propagates
- ❌ No connection → message silently dropped

**Impact**: 🟡 MEDIUM - Dashboard won't show real-time updates

---

### 5. Dashboard API (`api/dashboard.py`) - 253 lines, 2/7 tests passing

**Integration test failures**:
```
FAILED test_health_endpoint - RuntimeError: Redis not connected
FAILED test_status_endpoint - RuntimeError: Redis not connected
FAILED test_list_tasks_endpoint - assert 422 == 200
FAILED test_get_nonexistent_task - assert 422 == 404
```

**What can break**:
```python
# Line 31: Redis dependency
queue_length = await redis_client.queue_length()

# Line 176-218: Chat endpoint
session_db = SessionDB(...)
task_db = TaskDB(...)
await redis_client.push_task(task_id)
```

**Risks**:
- ❌ Redis down → health check fails
- ❌ Database write fails → task not created but user thinks it is
- ❌ Validation errors → 422 responses
- ❌ No authentication → anyone can access

**Impact**: 🟡 MEDIUM - Dashboard unusable but webhooks still work

---

### 6. Webhook Handlers (`api/webhooks.py`) - 178 lines, 1 test (failing)

**What can break**:
```python
# Line 25-44: GitHub webhook
payload = await request.json()
event_type = request.headers.get("X-GitHub-Event", "unknown")

# Line 55-96: Issue comment handling
if "@agent" in comment_body:
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    await redis_client.push_task(task_id)
```

**Risks**:
- ❌ No signature verification → anyone can trigger tasks
- ❌ Malformed payload → JSON parsing fails
- ❌ Missing headers → wrong event handling
- ❌ Database transaction fails → webhook returns 200 but task not created
- ❌ Infinite loop if task creates webhook that creates task

**Impact**: 🔴 HIGH - Security vulnerability + reliability issue

---

### 7. Background Manager (`core/background_manager.py`) - 115 lines, 0 tests

**What can break**:
```python
# Line 16: Semaphore for concurrency control
self._semaphore = asyncio.Semaphore(max_workers)

# Line 37-43: Task submission
async with self._semaphore:
    result = await runner_coro
```

**Risks**:
- ❌ Semaphore leak → tasks don't release slot
- ❌ Queue dictionary grows unbounded → memory leak
- ❌ Task cancellation doesn't clean up → zombie tasks

**Impact**: 🟡 MEDIUM - System degrades over time

---

## 🔥 Critical Process Flows NOT Tested End-to-End

### 1. Dashboard Chat Flow
```
User → POST /api/chat → Create Task → Redis Queue → Worker → CLI → WebSocket → User
```
**Missing tests**:
- Full flow from user input to response
- Error handling at each step
- Timeout scenarios
- Cost tracking accuracy

### 2. Webhook Flow
```
GitHub → POST /webhooks/github → Parse Event → Create Task → Process → Results
```
**Missing tests**:
- Signature verification
- Event parsing accuracy
- Task creation from webhook
- Response to GitHub

### 3. Agent Selection
```
Task with agent="planning" → Worker → CLI in /app/agents/planning/ → Uses planning CLAUDE.md
```
**Missing tests**:
- Agent directory resolution
- Fallback to brain if agent not found
- Agent-specific skills loading

### 4. Real-time Streaming
```
CLI output chunk → Worker → WebSocket Hub → All connected clients
```
**Missing tests**:
- Multi-client broadcasting
- Connection drops during streaming
- Output buffering and ordering

---

## 🐛 Specific Bugs Found in Integration Tests

### 1. Redis Not Connected Error
```python
# core/database/redis_client.py:125
async def queue_length(self) -> int:
    if not self._redis:
        raise RuntimeError("Redis not connected")
```
**Problem**: Tests don't mock Redis or start Redis
**Fix needed**: Mock Redis or use fakeredis

### 2. Validation Error (422) on List Tasks
```python
# api/dashboard.py:66
async def list_tasks(
    session_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session)
):
```
**Problem**: `get_session` dependency not provided in tests
**Fix needed**: Mock database session dependency

### 3. Internal Server Error (500) on GitHub Webhook
```
{"error": "_make_filtering_bound_logger.<locals>.make_method.<locals>.meth()
got multiple values for argument 'event'"}
```
**Problem**: structlog logger call has conflicting parameters
**Fix needed**: Fix logging call in webhook handler

---

## 🎯 Recommended Test Additions

### Priority 1 (Critical - System Breaking)
1. **Redis Client Tests**
   - Connection/disconnection
   - Queue operations (push, pop, length)
   - Error handling and retries

2. **Task Worker Tests**
   - Queue processing loop
   - CLI spawning and output handling
   - Database transaction handling
   - Error recovery

3. **CLI Runner Tests**
   - Subprocess spawning
   - Output streaming
   - Timeout handling
   - Error parsing

### Priority 2 (High - Feature Breaking)
4. **Integration Tests with Mocks**
   - Mock Redis and Database
   - Test all API endpoints
   - Test webhook handlers with signature verification

5. **WebSocket Tests**
   - Connection management
   - Broadcasting
   - Disconnect handling

### Priority 3 (Medium - Stability)
6. **E2E Tests**
   - Full dashboard chat flow
   - Full webhook flow
   - Agent selection flow
   - Cost tracking accuracy

7. **Performance Tests**
   - Concurrent task processing
   - Memory leak detection
   - Queue overflow handling

---

## 💊 Immediate Fixes Needed

### 1. Add Redis Mock to Tests
```python
# tests/conftest.py
@pytest.fixture
async def redis_mock():
    """Mock Redis for tests."""
    from unittest.mock import AsyncMock
    mock = AsyncMock()
    mock.queue_length.return_value = 0
    mock.push_task.return_value = None
    mock.pop_task.return_value = None
    return mock
```

### 2. Fix Webhook Logging Error
```python
# api/webhooks.py:43
# Current (broken):
logger.error("GitHub webhook error", error=str(e))

# Fixed:
logger.error("GitHub webhook error", error_message=str(e))
```

### 3. Add Database Session Mock
```python
# tests/conftest.py
@pytest.fixture
def override_get_session(db_session):
    """Override database dependency."""
    from api.dashboard import get_session
    app.dependency_overrides[get_session] = lambda: db_session
```

---

## 📊 Test Coverage Goals

Current: **15%** (models only)
Target: **80%** (industry standard)

**Breakdown needed**:
- Unit tests: 50% (business logic)
- Integration tests: 25% (API + database)
- E2E tests: 5% (critical flows)

---

## 🚨 What WILL Break in Production

### Guaranteed Failures:
1. ✅ **Redis connection loss** → Entire system stops
2. ✅ **Database transaction failure** → Tasks stuck in limbo
3. ✅ **WebSocket disconnect** → Output lost forever
4. ✅ **Claude CLI not installed** → All tasks fail
5. ✅ **Malicious webhook payload** → Code injection possible

### Probable Failures:
6. **High load** → Queue overflow, memory leak
7. **Long-running tasks** → Timeout not handled gracefully
8. **Concurrent tasks** → Race conditions in status updates
9. **Agent directory missing** → No fallback logic
10. **Invalid JSON from CLI** → Parser crashes

### Edge Cases:
11. Multiple workers processing same task
12. Task canceled mid-execution
13. WebSocket client reconnect during streaming
14. Redis queue corruption
15. SQLite database locked

---

## 🎓 Conclusion

**Current State**:
- ✅ Pydantic models are well-tested and safe
- ❌ All integration code is untested
- ❌ Process flows are not verified
- ❌ Error handling is not tested

**Recommendation**:
**DO NOT deploy to production** without adding:
1. Redis integration tests
2. Task worker tests
3. Webhook security tests
4. Error handling tests

The system will appear to work in development but will fail unpredictably in production under load or when external services (Redis, Claude CLI) have issues.
