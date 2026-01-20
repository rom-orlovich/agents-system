# Pydantic Migration & Code Cleanup Plan

## Overview

Refactor the codebase to properly leverage Pydantic models for data validation and integrity across the webhook → Redis → Planning → Executor pipeline. Additionally, remove dead/unused code to reduce maintenance burden.

**Current Problem:**
- Pydantic models exist in `shared/models.py` but are mostly unused
- `shared/types.py` duplicates some structures as dataclasses
- Data flows through the system as raw dictionaries (`Dict[str, Any]`)
- No validation happens at system boundaries
- Some modules (`database.py`) are completely unused

---

## Project Type

**BACKEND** - Data model refactoring and code cleanup

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Type Safety | All queue push/pop operations use Pydantic models |
| Validation | Input data validated at webhook entry points |
| Serialization | JSON serialization/deserialization via Pydantic |
| Code Reduction | Unused files and duplicate definitions removed |
| Tests Pass | All existing tests continue to pass |

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Data Models | Pydantic v2 | Already in use, provides validation + serialization |
| Queue | Redis + Pydantic | Type-safe task queue operations |
| Enums | Python Enum (str, Enum) | Already standardized in `enums.py` |

---

## Analysis: Current State

### Files Analyzed

| File | Purpose | Status |
|------|---------|--------|
| `shared/models.py` | Pydantic models (Task, DiscoveryResult, etc.) | 🔶 Defined but mostly unused |
| `shared/types.py` | Dataclasses (OAuthCredentials, GitRepository, etc.) | ✅ Actively used |
| `shared/enums.py` | All enums (TaskStatus, TaskSource, etc.) | ✅ Correctly centralized |
| `shared/task_queue.py` | Redis queue operations | 🔶 Uses raw dicts - needs Pydantic |
| `shared/database.py` | PostgreSQL models | ❌ **UNUSED** - can be removed |
| `shared/constants.py` | Configuration constants | ✅ Actively used |
| `shared/github_client.py` | Webhook validation utilities | ✅ Actively used (minimal) |

### Current Data Flow (Problem)

```
Webhook (jira.py) → Dict[str, Any] → RedisQueue.push() 
                                          ↓
                         JSON string in Redis
                                          ↓
                     RedisQueue.pop() → Dict[str, Any]
                                          ↓
                       Worker accesses via dict["key"]
```

**Issues:**
1. No validation at entry point
2. No type hints for worker consumption
3. Typos in keys cause runtime failures
4. Missing fields not caught until runtime

### Target Data Flow (Solution)

```
Webhook (jira.py) → JiraTask(**payload) → Validated Pydantic
                                          ↓
                       task.model_dump_json() → Redis
                                          ↓
                     RedisQueue.pop() → JiraTask.model_validate_json()
                                          ↓
                       Worker accesses via task.issue_key (typed)
```

---

## Proposed Changes

### Phase 1: Define Task Models

#### [MODIFY] [models.py](file:///Users/romo/projects/agents-prod/claude-code-cli/shared/models.py)

Refine the `Task` model and add specialized task types:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from .enums import TaskStatus, TaskSource

class BaseTask(BaseModel):
    """Base task with common fields."""
    task_id: str = Field(default_factory=lambda: f"task-{datetime.now().timestamp()}")
    source: TaskSource
    status: TaskStatus = TaskStatus.QUEUED
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    
class JiraTask(BaseTask):
    """Task from Jira webhook."""
    source: Literal[TaskSource.JIRA] = TaskSource.JIRA
    action: Literal["enrich", "fix", "approve"]
    issue_key: str
    description: str = ""
    full_description: str = ""
    sentry_issue_id: Optional[str] = None
    repository: Optional[str] = None

class SentryTask(BaseTask):
    """Task from Sentry webhook."""
    source: Literal[TaskSource.SENTRY] = TaskSource.SENTRY
    sentry_issue_id: str
    description: str
    repository: str

class GitHubTask(BaseTask):
    """Task from GitHub webhook."""
    source: Literal[TaskSource.GITHUB] = TaskSource.GITHUB
    repository: str
    pr_number: Optional[int] = None
    comment: Optional[str] = None

# Union type for queue operations
AnyTask = JiraTask | SentryTask | GitHubTask
```

**Rationale:** Specialized task types provide:
- Type narrowing based on `source` field
- Required fields per source (e.g., `issue_key` for Jira)
- Better IDE autocomplete

---

### Phase 2: Refactor Task Queue

#### [MODIFY] [task_queue.py](file:///Users/romo/projects/agents-prod/claude-code-cli/shared/task_queue.py)

Add Pydantic-aware push/pop methods:

```python
from pydantic import BaseModel
from .models import AnyTask, JiraTask, SentryTask, GitHubTask

class RedisQueue:
    async def push_task(self, queue_name: str, task: BaseModel) -> str:
        """Push a Pydantic task to the queue.
        
        Args:
            queue_name: Name of the queue
            task: Pydantic model instance
        
        Returns:
            Task ID
        """
        await self.connect()
        
        # Serialize using Pydantic v2
        data = task.model_dump_json()
        
        # Store in queue
        await self.redis.lpush(queue_name, data)
        
        # Store task metadata
        await self.redis.hset(
            f"tasks:{task.task_id}",
            mapping={
                "data": data,
                "status": task.status.value,
                "queue": queue_name
            }
        )
        return task.task_id

    async def pop_task(self, queue_name: str, timeout: int = 0) -> Optional[AnyTask]:
        """Pop a validated task from the queue.
        
        Returns:
            Validated Pydantic task or None
        """
        await self.connect()
        result = await self.redis.brpop(queue_name, timeout=timeout)
        
        if result:
            _, data = result
            # Discriminated union parsing
            return self._parse_task(data)
        return None

    def _parse_task(self, json_str: str) -> AnyTask:
        """Parse JSON to appropriate task type."""
        import json
        raw = json.loads(json_str)
        source = raw.get("source", "")
        
        if source == TaskSource.JIRA.value:
            return JiraTask.model_validate(raw)
        elif source == TaskSource.SENTRY.value:
            return SentryTask.model_validate(raw)
        elif source == TaskSource.GITHUB.value:
            return GitHubTask.model_validate(raw)
        else:
            raise ValueError(f"Unknown task source: {source}")
```

---

### Phase 3: Refactor Webhook Routes

#### [MODIFY] [jira.py](file:///Users/romo/projects/agents-prod/claude-code-cli/services/webhook-server/routes/jira.py)

Use Pydantic models for task creation:

```diff
- task_data = {
-     "source": TaskSource.JIRA.value,
-     "action": action,
-     "description": summary,
-     "issue_key": issue_key,
-     ...
- }
- task_id = await queue.push(settings.PLANNING_QUEUE, task_data)

+ from shared.models import JiraTask
+ 
+ task = JiraTask(
+     action=action,
+     issue_key=issue_key,
+     description=summary,
+     sentry_issue_id=sentry_issue_id,
+     repository=repository,
+     full_description=description[:10000]
+ )
+ task_id = await queue.push_task(settings.PLANNING_QUEUE, task)
```

#### [MODIFY] [sentry.py](file:///Users/romo/projects/agents-prod/claude-code-cli/services/webhook-server/routes/sentry.py)

```diff
- task_data = {
-     "source": TaskSource.SENTRY.value,
-     "description": event_data.get("message"),
-     ...
- }

+ from shared.models import SentryTask
+ 
+ task = SentryTask(
+     sentry_issue_id=payload.get("id"),
+     description=event_data.get("message") or "Sentry error",
+     repository=repository
+ )
```

---

### Phase 4: Refactor Workers

#### [MODIFY] [worker.py (planning)](file:///Users/romo/projects/agents-prod/claude-code-cli/agents/planning-agent/worker.py)

Update to consume typed tasks:

```diff
- task_data = await self.queue.pop(self.queue_name, timeout=0)
- if task_data:
-     action = task_data.get("action", "default")
-     issue_key = task_data.get("issue_key")

+ task = await self.queue.pop_task(self.queue_name, timeout=0)
+ if task:
+     if isinstance(task, JiraTask):
+         action = task.action
+         issue_key = task.issue_key
```

#### [MODIFY] [worker.py (executor)](file:///Users/romo/projects/agents-prod/claude-code-cli/agents/executor-agent/worker.py)

Same pattern - consume typed tasks instead of dicts.

---

### Phase 5: Remove Unused Code

> [!CAUTION]
> **Breaking Change Risk:** Ensure no external services depend on these files before deletion.

#### [DELETE] [database.py](file:///Users/romo/projects/agents-prod/claude-code-cli/shared/database.py)

**Reason:** Not imported anywhere in the codebase. The system uses Redis, not PostgreSQL.

```bash
# Verify no usages
grep -r "from shared.database" . --include="*.py"
# Returns: No results
```

#### [MODIFY] [models.py](file:///Users/romo/projects/agents-prod/claude-code-cli/shared/models.py)

Remove unused models that were never integrated:

| Model | Status | Action |
|-------|--------|--------|
| `DiscoveryResult` | Unused | **REMOVE** |
| `ExecutionStep` | Unused | **REMOVE** |
| `ExecutionPlan` | Unused | **REMOVE** |
| `SentryAnalysis` | Unused | **REMOVE** |
| `ExecutionResult` | Unused | **REMOVE** |
| `ApprovalRequest` | Unused | **REMOVE** |
| `WebhookPayload` | Unused | **REMOVE** |
| `Task` | Partially used | **REFACTOR** → `BaseTask` + specialized types |

#### [MODIFY] [types.py](file:///Users/romo/projects/agents-prod/claude-code-cli/shared/types.py)

Clean up unused types and TypedDicts:

| Type | Status | Action |
|------|--------|--------|
| `TaskContext` | Unused | **REMOVE** |
| `GitHubCommentContext` | Unused (TypedDict) | **REMOVE** |
| `JiraCommentContext` | Unused (TypedDict) | **REMOVE** |
| `SlackMessageContext` | Unused (TypedDict) | **KEEP** (might be used in future) |
| `OAuthCredentials` | Used | **KEEP** (used in token_manager) |
| `GitRepository` | Used | **KEEP** |
| `CommandDefinition` | Used | **KEEP** |

---

## File Structure After Changes

```
shared/
├── __init__.py
├── config.py              # Configuration (unchanged)
├── constants.py           # Constants (unchanged)
├── enums.py               # Enums (unchanged)
├── models.py              # [MODIFIED] Pydantic task models
├── types.py               # [MODIFIED] Remove unused types
├── task_queue.py          # [MODIFIED] Pydantic-aware methods
├── github_client.py       # Webhook validation (unchanged)
├── slack_client.py        # Slack API (unchanged)
├── git_utils.py           # Git operations (unchanged)
├── token_manager.py       # OAuth (unchanged)
├── logging_utils.py       # Logging (unchanged)
├── metrics.py             # Metrics (unchanged)
├── claude_runner.py       # CLI runner (unchanged)
├── ensure_auth.py         # Auth check (unchanged)
└── commands/              # Command system (unchanged)

# DELETED:
# - shared/database.py (unused PostgreSQL)
```

---

## Task Breakdown

### Phase 1: Define Task Models
- [ ] **T1.1**: Refactor `shared/models.py` - Create `BaseTask`, `JiraTask`, `SentryTask`, `GitHubTask`
  - INPUT: Current `models.py`
  - OUTPUT: New Pydantic models with discriminated union
  - VERIFY: `python -c "from shared.models import JiraTask; print(JiraTask.model_json_schema())"`
  - AGENT: `backend-specialist`

### Phase 2: Refactor Task Queue
- [ ] **T2.1**: Add `push_task()` and `pop_task()` methods to `RedisQueue`
  - INPUT: Current `task_queue.py`
  - OUTPUT: Pydantic-aware queue methods
  - VERIFY: Unit test with mock Redis
  - AGENT: `backend-specialist`
  - DEPENDS: T1.1

### Phase 3: Refactor Webhooks
- [ ] **T3.1**: Update `routes/jira.py` to use `JiraTask`
  - VERIFY: Send test webhook, check task in Redis is valid JSON
  - AGENT: `backend-specialist`
  - DEPENDS: T2.1

- [ ] **T3.2**: Update `routes/sentry.py` to use `SentryTask`
  - AGENT: `backend-specialist`
  - DEPENDS: T2.1

- [ ] **T3.3**: Update `routes/github.py` to use `GitHubTask`
  - AGENT: `backend-specialist`
  - DEPENDS: T2.1

- [ ] **T3.4**: Update `routes/slack.py` if needed
  - AGENT: `backend-specialist`
  - DEPENDS: T2.1

### Phase 4: Refactor Workers
- [ ] **T4.1**: Update `planning-agent/worker.py` to consume typed tasks
  - VERIFY: Worker starts, processes queue correctly
  - AGENT: `backend-specialist`
  - DEPENDS: T3.1, T3.2, T3.3

- [ ] **T4.2**: Update `executor-agent/worker.py` to consume typed tasks
  - VERIFY: Worker starts, processes queue correctly
  - AGENT: `backend-specialist`
  - DEPENDS: T4.1

### Phase 5: Remove Unused Code
- [ ] **T5.1**: Delete `shared/database.py`
  - VERIFY: `grep -r "database" . --include="*.py"` returns no imports
  - AGENT: `backend-specialist`

- [ ] **T5.2**: Remove unused models from `shared/models.py`
  - VERIFY: No import errors
  - AGENT: `backend-specialist`
  - DEPENDS: T4.2

- [ ] **T5.3**: Clean up unused types from `shared/types.py`
  - VERIFY: No import errors
  - AGENT: `backend-specialist`
  - DEPENDS: T4.2

### Phase X: Verification
- [ ] **TX.1**: Run all tests
  - COMMAND: `pytest tests/`
  - AGENT: `test-engineer`
  - DEPENDS: T5.3

- [ ] **TX.2**: Manual smoke test
  - Send test Jira webhook
  - Verify task appears in Redis correctly
  - Verify planning-agent processes it
  - AGENT: `test-engineer`

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing queue data | Tasks in Redis become unreadable | Deploy during low-traffic window; drain queue first |
| Type errors during migration | Runtime failures | Add comprehensive unit tests before refactoring |
| Missing task fields | Validation errors | Use `Optional` with defaults for backwards compatibility |

---

## Verification Checklist

- [ ] Lint passes: `make lint`
- [ ] Type check passes: `mypy shared/`
- [ ] Unit tests pass: `pytest tests/`
- [ ] Docker build succeeds: `make build`
- [ ] Manual test: webhook → Redis → worker flow works

---

## Next Steps

After approval:
1. Run `/create` to start implementation
2. Or proceed manually with Phase 1
