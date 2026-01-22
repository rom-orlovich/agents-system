# Dashboard Features Implementation Plan

> **Comprehensive guide for implementing missing dashboard features in claude-code-agent**

---

## Critical Review & Alignment Analysis

### ✅ What Aligns Well

| Aspect | Current Project | Plan Alignment |
|--------|-----------------|----------------|
| **Database** | SQLAlchemy async + SQLite | ✅ Plan uses same patterns |
| **API Framework** | FastAPI with async | ✅ Plan follows existing router patterns |
| **Models** | Pydantic with validation | ✅ Plan extends existing models |
| **Testing** | pytest-asyncio + fixtures | ✅ Plan can use existing infrastructure |
| **Config** | `core/config.py` with paths | ✅ Plan uses existing `credentials_path`, `user_skills_dir` |
| **Auth Model** | `ClaudeCredentials` exists | ✅ Plan reuses it for upload validation |

### ⚠️ Issues & Gaps Identified

| Issue | Severity | Problem | Fix Required |
|-------|----------|---------|--------------|
| **Missing `parent_task_id` index** | Medium | Plan assumes `parent_task_id` is indexed for subagent log queries | Add index to `TaskDB.parent_task_id` |
| **No `SubagentLogDB` relationship** | High | Plan proposes FK to `tasks.task_id` but `TaskDB` doesn't define backref | Add relationship in migration |
| **Redis rate limit caching** | Medium | Plan assumes `redis_client.get/set` but current client uses custom methods | Use existing `redis_client` patterns |
| **`APIResponse` import** | Low | Plan uses `APIResponse` - already exists in `shared` | ✅ No change needed |
| **Missing `aiofiles` dependency** | Medium | Plan uses `aiofiles` for async file writes | Add to `pyproject.toml` |
| **Chart.js via CDN** | Low | Plan uses CDN - works but consider bundling for offline | Acceptable for MVP |
| **No pagination in existing `/tasks`** | Medium | Current endpoint has `limit` but no `page/offset` | Plan correctly adds pagination |

### 🚫 Potential Breaking Changes

1. **Database Migration Required**: Adding `SubagentLogDB` table requires Alembic migration
2. **New API Routes**: Must register new routers in `main.py`
3. **Frontend Changes**: `index.html` and `app.js` need significant updates

### 📋 Missing from Plan

| Missing Item | Impact | Recommendation |
|--------------|--------|----------------|
| **Alembic migration scripts** | High | Add migration commands to plan |
| **Router registration** | Medium | Show how to add routers to `main.py` |
| **WebSocket updates for new features** | Medium | Extend `WSMessage` union type |
| **Error handling patterns** | Medium | Follow existing `HTTPException` patterns |
| **TDD test specifications** | **Critical** | **Must add before implementation** |

---

## TDD Requirements

> **All business logic MUST have tests written BEFORE implementation**

### Testing Strategy

```
tests/
├── unit/
│   ├── test_models.py              # Existing - extend
│   ├── test_credential_service.py  # NEW - credential validation logic
│   ├── test_analytics_service.py   # NEW - cost aggregation logic
│   └── test_registry_service.py    # NEW - skill/agent management
├── integration/
│   ├── test_api.py                 # Existing - extend
│   ├── test_credentials_api.py     # NEW - upload/status endpoints
│   ├── test_analytics_api.py       # NEW - chart data endpoints
│   └── test_registry_api.py        # NEW - skills/agents CRUD
└── fixtures/
    ├── credential_fixtures.py      # NEW - mock credentials
    └── analytics_fixtures.py       # NEW - sample cost data
```

### Test-First Implementation Order

For each feature, write tests in this order:
1. **Unit tests** for business logic (models, services)
2. **Integration tests** for API endpoints
3. **Implementation** of the feature
4. **Verify** all tests pass

---

## TDD Test Specifications by Feature

### Feature 4: Credential Management (P0 - Write Tests First)

```python
# tests/unit/test_credential_service.py

import pytest
from datetime import datetime, timedelta
from shared import ClaudeCredentials, AuthStatus

class TestClaudeCredentials:
    """Test credential validation logic."""
    
    def test_valid_credentials(self):
        """Valid credentials return VALID status."""
        future_ts = int((datetime.utcnow() + timedelta(hours=2)).timestamp() * 1000)
        creds = ClaudeCredentials(
            access_token="valid_token_12345",
            refresh_token="refresh_token_12345",
            expires_at=future_ts,
        )
        assert creds.get_status() == AuthStatus.VALID
        assert not creds.is_expired
        assert not creds.needs_refresh
    
    def test_expired_credentials(self):
        """Expired credentials return EXPIRED status."""
        past_ts = int((datetime.utcnow() - timedelta(hours=1)).timestamp() * 1000)
        creds = ClaudeCredentials(
            access_token="expired_token_12345",
            refresh_token="refresh_token_12345",
            expires_at=past_ts,
        )
        assert creds.get_status() == AuthStatus.EXPIRED
        assert creds.is_expired
    
    def test_needs_refresh_credentials(self):
        """Credentials expiring within 30 min return REFRESH_NEEDED."""
        soon_ts = int((datetime.utcnow() + timedelta(minutes=15)).timestamp() * 1000)
        creds = ClaudeCredentials(
            access_token="soon_expired_token",
            refresh_token="refresh_token_12345",
            expires_at=soon_ts,
        )
        assert creds.get_status() == AuthStatus.REFRESH_NEEDED
        assert creds.needs_refresh
        assert not creds.is_expired
    
    def test_invalid_token_format(self):
        """Short tokens are rejected."""
        with pytest.raises(ValueError):
            ClaudeCredentials(
                access_token="short",  # < 10 chars
                refresh_token="refresh_token_12345",
                expires_at=1234567890000,
            )


# tests/integration/test_credentials_api.py

import pytest
from httpx import AsyncClient
import json

@pytest.mark.integration
@pytest.mark.asyncio
class TestCredentialsAPI:
    """Integration tests for credential endpoints."""
    
    async def test_status_missing_credentials(self, client: AsyncClient, tmp_path, monkeypatch):
        """Status returns MISSING when no credentials file."""
        monkeypatch.setattr("core.config.settings.credentials_path", tmp_path / "nonexistent.json")
        
        response = await client.get("/api/credentials/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "missing"
        assert data["cli_available"] in [True, False]  # Depends on environment
    
    async def test_upload_valid_credentials(self, client: AsyncClient, tmp_path, monkeypatch):
        """Upload valid credentials file succeeds."""
        monkeypatch.setattr("core.config.settings.credentials_path", tmp_path / "claude.json")
        
        future_ts = int((datetime.utcnow() + timedelta(hours=2)).timestamp() * 1000)
        creds_content = json.dumps({
            "access_token": "valid_access_token_12345",
            "refresh_token": "valid_refresh_token_12345",
            "expires_at": future_ts,
        })
        
        response = await client.post(
            "/api/credentials/upload",
            files={"file": ("claude.json", creds_content, "application/json")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "expires_at" in data["data"]
    
    async def test_upload_expired_credentials_rejected(self, client: AsyncClient, tmp_path, monkeypatch):
        """Upload expired credentials is rejected."""
        monkeypatch.setattr("core.config.settings.credentials_path", tmp_path / "claude.json")
        
        past_ts = int((datetime.utcnow() - timedelta(hours=1)).timestamp() * 1000)
        creds_content = json.dumps({
            "access_token": "expired_access_token_12345",
            "refresh_token": "expired_refresh_token_12345",
            "expires_at": past_ts,
        })
        
        response = await client.post(
            "/api/credentials/upload",
            files={"file": ("claude.json", creds_content, "application/json")}
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()
    
    async def test_upload_invalid_json_rejected(self, client: AsyncClient):
        """Upload invalid JSON is rejected."""
        response = await client.post(
            "/api/credentials/upload",
            files={"file": ("claude.json", "not valid json", "application/json")}
        )
        assert response.status_code == 400
    
    async def test_upload_non_json_file_rejected(self, client: AsyncClient):
        """Upload non-JSON file is rejected."""
        response = await client.post(
            "/api/credentials/upload",
            files={"file": ("credentials.txt", "some text", "text/plain")}
        )
        assert response.status_code == 400
```

### Feature 2: Enhanced Task Table (P1 - Write Tests First)

```python
# tests/integration/test_task_table_api.py

import pytest
from httpx import AsyncClient
from datetime import datetime

@pytest.mark.integration
@pytest.mark.asyncio
class TestTaskTableAPI:
    """Integration tests for paginated task table."""
    
    async def test_task_table_empty(self, client: AsyncClient):
        """Empty database returns empty list with pagination info."""
        response = await client.get("/api/tasks/table")
        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["total_pages"] == 0
    
    async def test_task_table_pagination(self, client: AsyncClient, db_session):
        """Pagination returns correct page of results."""
        # Create 25 tasks
        from core.database.models import TaskDB, SessionDB
        
        session = SessionDB(session_id="test-sess", user_id="user-1", machine_id="m-1")
        db_session.add(session)
        
        for i in range(25):
            task = TaskDB(
                task_id=f"task-{i:03d}",
                session_id="test-sess",
                user_id="user-1",
                agent_type="planning",
                status="completed",
                input_message=f"Task {i}",
                cost_usd=0.01 * i,
            )
            db_session.add(task)
        await db_session.commit()
        
        # Page 1 (default page_size=20)
        response = await client.get("/api/tasks/table?page=1&page_size=10")
        data = response.json()
        assert len(data["tasks"]) == 10
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["total_pages"] == 3
        
        # Page 3
        response = await client.get("/api/tasks/table?page=3&page_size=10")
        data = response.json()
        assert len(data["tasks"]) == 5  # Remaining tasks
        assert data["page"] == 3
    
    async def test_task_table_filter_by_status(self, client: AsyncClient, db_session):
        """Filter by status returns only matching tasks."""
        # Setup: Create tasks with different statuses
        # ... (similar setup as above)
        
        response = await client.get("/api/tasks/table?status=completed")
        data = response.json()
        for task in data["tasks"]:
            assert task["status"] == "completed"
    
    async def test_task_table_sort_by_cost(self, client: AsyncClient, db_session):
        """Sort by cost_usd works correctly."""
        response = await client.get("/api/tasks/table?sort_by=cost_usd&sort_order=desc")
        data = response.json()
        costs = [t["cost_usd"] for t in data["tasks"]]
        assert costs == sorted(costs, reverse=True)
```

### Feature 3: Cost Analytics (P1 - Write Tests First)

```python
# tests/unit/test_analytics_service.py

import pytest
from datetime import datetime, timedelta

class TestCostAggregation:
    """Test cost aggregation logic."""
    
    def test_daily_cost_aggregation(self, db_session):
        """Daily costs are correctly aggregated."""
        # This tests the SQL query logic
        pass  # Implement with actual DB fixtures
    
    def test_subagent_cost_breakdown(self, db_session):
        """Costs are correctly grouped by subagent."""
        pass
    
    def test_empty_date_range(self, db_session):
        """Empty date range returns zeros."""
        pass


# tests/integration/test_analytics_api.py

@pytest.mark.integration
@pytest.mark.asyncio
class TestAnalyticsAPI:
    """Integration tests for analytics endpoints."""
    
    async def test_analytics_summary_empty(self, client: AsyncClient):
        """Summary with no tasks returns zeros."""
        response = await client.get("/api/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["today_cost"] == 0.0
        assert data["today_tasks"] == 0
        assert data["total_cost"] == 0.0
        assert data["total_tasks"] == 0
    
    async def test_daily_costs_format(self, client: AsyncClient, db_session):
        """Daily costs returns correct format for Chart.js."""
        response = await client.get("/api/analytics/costs/daily?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "dates" in data
        assert "costs" in data
        assert "task_counts" in data
        assert isinstance(data["dates"], list)
        assert isinstance(data["costs"], list)
        assert len(data["dates"]) == len(data["costs"])
    
    async def test_subagent_costs_format(self, client: AsyncClient):
        """Subagent costs returns correct format for Chart.js."""
        response = await client.get("/api/analytics/costs/by-subagent")
        assert response.status_code == 200
        data = response.json()
        assert "subagents" in data
        assert "costs" in data
```

### Feature 5: Skills/Agent Registry (P3 - Write Tests First)

```python
# tests/unit/test_registry_service.py

import pytest
from pathlib import Path

class TestSkillValidation:
    """Test skill folder validation."""
    
    def test_valid_skill_structure(self, tmp_path):
        """Valid skill folder is accepted."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# My Skill\n\nDescription")
        
        # Validation logic should pass
        assert (skill_dir / "SKILL.md").exists()
    
    def test_skill_with_scripts(self, tmp_path):
        """Skill with scripts is accepted."""
        skill_dir = tmp_path / "script-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Script Skill")
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.py").write_text("print('hello')")
        
        assert (scripts_dir / "run.py").exists()


# tests/integration/test_registry_api.py

@pytest.mark.integration
@pytest.mark.asyncio
class TestRegistryAPI:
    """Integration tests for registry endpoints."""
    
    async def test_list_skills_includes_builtin(self, client: AsyncClient):
        """List skills includes built-in skills."""
        response = await client.get("/api/registry/skills")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least some built-in skills
    
    async def test_upload_skill(self, client: AsyncClient, tmp_path, monkeypatch):
        """Upload skill creates folder."""
        monkeypatch.setattr("core.config.settings.user_skills_dir", tmp_path)
        
        response = await client.post(
            "/api/registry/skills/upload",
            data={"name": "test-skill"},
            files=[
                ("files", ("SKILL.md", "# Test Skill", "text/markdown")),
            ]
        )
        assert response.status_code == 200
        assert (tmp_path / "test-skill" / "SKILL.md").exists()
    
    async def test_delete_user_skill(self, client: AsyncClient, tmp_path, monkeypatch):
        """Delete user skill removes folder."""
        monkeypatch.setattr("core.config.settings.user_skills_dir", tmp_path)
        
        # Create skill first
        skill_dir = tmp_path / "to-delete"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# To Delete")
        
        response = await client.delete("/api/registry/skills/to-delete")
        assert response.status_code == 200
        assert not skill_dir.exists()
    
    async def test_delete_builtin_skill_forbidden(self, client: AsyncClient):
        """Cannot delete built-in skills."""
        # Built-in skills are in /app/skills, not /data/config/skills
        response = await client.delete("/api/registry/skills/some-builtin")
        assert response.status_code == 404  # Not found in user dir
```

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Feature 1: Subagent Logs Viewer](#3-feature-1-subagent-logs-viewer)
4. [Feature 2: Enhanced Task Table](#4-feature-2-enhanced-task-table)
5. [Feature 3: Cost Analytics Charts](#5-feature-3-cost-analytics-charts)
6. [Feature 4: Credential Management UI](#6-feature-4-credential-management-ui)
7. [Feature 5: Skills/Subagent Folder Management](#7-feature-5-skillssubagent-folder-management)
8. [Feature 6: Cloud Storage Integration](#8-feature-6-cloud-storage-integration)
9. [Implementation Timeline](#9-implementation-timeline)
10. [Technical Dependencies](#10-technical-dependencies)

---

## 1. Executive Summary

### Goals
- Enable visibility into subagent execution logs and traces
- Display comprehensive task metrics (cost, session, time, subagent) in dashboard
- Visualize cost analytics with interactive charts
- Provide credential upload UI when CLI is unavailable or rate-limited
- Support persistent skills/subagent folder configuration
- Enable cloud storage for credentials and configuration

### Priority Order
1. **P0 (Critical)**: Credential Management UI - blocks usage when credentials missing
2. **P1 (High)**: Enhanced Task Table - core visibility feature
3. **P1 (High)**: Cost Analytics Charts - budget management
4. **P2 (Medium)**: Subagent Logs Viewer - debugging capability
5. **P3 (Low)**: Skills/Subagent Folder Management - power user feature
6. **P3 (Low)**: Cloud Storage Integration - enterprise feature

---

## 2. Current State Analysis

### What Exists

| Component | Location | Status |
|-----------|----------|--------|
| Task database model | `core/database/models.py:30-67` | ✅ Has cost, tokens, duration, session_id |
| Dashboard API | `api/dashboard.py` | ✅ Basic CRUD for tasks/sessions |
| Dashboard UI | `services/dashboard/static/` | ⚠️ Minimal - chat + task cards only |
| Credentials model | `shared/machine_models.py:303-335` | ✅ Has expiry/refresh checks |
| Config paths | `core/config.py:58-86` | ✅ Has user_agents_dir, user_skills_dir |
| Subagent config | `core/subagent_config.py` | ✅ Loads from subagents.json |

### What's Missing

| Feature | Gap |
|---------|-----|
| Subagent logs | No dedicated storage/viewer for execution traces |
| Task table UI | No table view with sortable columns |
| Cost charts | No Chart.js or visualization library |
| Credential upload | No API endpoint or UI component |
| CLI health check | No endpoint to detect CLI availability/limits |
| Folder management | No UI for uploading skills/agents |

---

## 3. Feature 1: Subagent Logs Viewer

### 3.1 Overview

Capture and display execution logs from subagents with distributed tracing support.

**Reference**: [AI Agent Observability Best Practices](https://dev.to/kuldeep_paul/a-comprehensive-guide-to-observability-in-ai-agents-best-practices-4bd4)

### 3.2 Database Schema

```python
# core/database/models.py - Add new model

class SubagentLogDB(Base):
    """Subagent execution log entry."""
    __tablename__ = "subagent_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), ForeignKey("tasks.task_id"), nullable=False, index=True)
    parent_task_id = Column(String(255), nullable=True, index=True)
    
    # Trace context
    trace_id = Column(String(64), nullable=False, index=True)
    span_id = Column(String(32), nullable=False)
    parent_span_id = Column(String(32), nullable=True)
    
    # Subagent info
    subagent_name = Column(String(255), nullable=False)
    subagent_type = Column(String(50), nullable=False)  # planning, executor, etc.
    
    # Execution details
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0)
    
    # Input/Output
    input_prompt = Column(Text, nullable=True)
    output_result = Column(Text, nullable=True)
    
    # Metrics
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    
    # Tool calls
    tool_calls = Column(Text, default="[]")  # JSON array
    
    # Status
    status = Column(String(50), nullable=False)  # running, completed, failed
    error = Column(Text, nullable=True)
    
    # Relationships
    task = relationship("TaskDB", backref="subagent_logs")
```

### 3.3 API Endpoints

```python
# api/subagent_logs.py

@router.get("/tasks/{task_id}/logs")
async def get_task_subagent_logs(
    task_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> List[SubagentLogResponse]:
    """Get all subagent execution logs for a task."""
    pass

@router.get("/logs/{trace_id}")
async def get_trace_logs(
    trace_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> TraceResponse:
    """Get complete trace with all spans."""
    pass

@router.get("/logs/search")
async def search_logs(
    subagent_name: str | None = None,
    status: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
) -> List[SubagentLogResponse]:
    """Search subagent logs with filters."""
    pass
```

### 3.4 Log Capture Integration

```python
# workers/task_worker.py - Modify run_claude_cli

async def run_claude_cli(...):
    # Generate trace context
    trace_id = generate_trace_id()
    span_id = generate_span_id()
    
    # Create log entry at start
    log_entry = SubagentLogDB(
        task_id=task_id,
        trace_id=trace_id,
        span_id=span_id,
        subagent_name=agent_name,
        subagent_type=agent_type,
        started_at=datetime.utcnow(),
        status="running",
        input_prompt=prompt[:10000],  # Truncate
    )
    
    # ... execute CLI ...
    
    # Update log entry on completion
    log_entry.completed_at = datetime.utcnow()
    log_entry.duration_ms = (log_entry.completed_at - log_entry.started_at).total_seconds() * 1000
    log_entry.output_result = result[:10000]
    log_entry.input_tokens = metrics.input_tokens
    log_entry.output_tokens = metrics.output_tokens
    log_entry.cost_usd = metrics.cost_usd
    log_entry.tool_calls = json.dumps(tool_calls)
    log_entry.status = "completed" if not error else "failed"
```

### 3.5 UI Component

```html
<!-- Subagent Logs Panel -->
<section class="panel logs-panel">
    <h2>Subagent Execution Logs</h2>
    <div class="logs-filters">
        <select id="log-subagent-filter">
            <option value="">All Subagents</option>
            <option value="planning">Planning</option>
            <option value="executor">Executor</option>
        </select>
        <select id="log-status-filter">
            <option value="">All Status</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
        </select>
    </div>
    <div id="logs-timeline" class="logs-timeline">
        <!-- Rendered via JS -->
    </div>
</section>
```

### 3.6 Metrics to Track

Based on AI observability best practices:

| Metric | Description |
|--------|-------------|
| **Token usage** | Input/output tokens per subagent call |
| **Tool interactions** | Which tools invoked, success rates |
| **Reasoning traces** | Decision flow and plan adjustments |
| **Quality indicators** | Task completion rate, error rate |
| **Latency breakdown** | Time per step in execution |

---

## 4. Feature 2: Enhanced Task Table

### 4.1 Overview

Replace the simple task cards with a full-featured data table showing:
- Task ID, Session ID, Cost (USD), Duration, Subagent name, Created/Completed time, Status

### 4.2 API Enhancement

```python
# api/dashboard.py - Enhanced task list endpoint

@router.get("/tasks/table")
async def list_tasks_table(
    db: AsyncSession = Depends(get_db_session),
    session_id: str | None = Query(None),
    status: str | None = Query(None),
    subagent: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TaskTableResponse:
    """List tasks with pagination and sorting for table view."""
    query = select(TaskDB)
    
    # Apply filters
    if session_id:
        query = query.where(TaskDB.session_id == session_id)
    if status:
        query = query.where(TaskDB.status == status)
    if subagent:
        query = query.where(TaskDB.assigned_agent == subagent)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Apply sorting and pagination
    sort_column = getattr(TaskDB, sort_by, TaskDB.created_at)
    query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return TaskTableResponse(
        tasks=[TaskTableRow.from_db(t) for t in tasks],
        total=total, page=page, page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )
```

### 4.3 UI: Task Table HTML

```html
<section class="panel tasks-table-panel">
    <h2>Task History</h2>
    <div class="table-filters">
        <input type="text" id="filter-session" placeholder="Session ID...">
        <select id="filter-status">
            <option value="">All Status</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
        </select>
        <select id="filter-subagent">
            <option value="">All Subagents</option>
        </select>
    </div>
    <table id="tasks-table">
        <thead>
            <tr>
                <th data-sort="task_id">Task ID</th>
                <th data-sort="session_id">Session</th>
                <th data-sort="assigned_agent">Subagent</th>
                <th data-sort="status">Status</th>
                <th data-sort="cost_usd">Cost</th>
                <th data-sort="duration_seconds">Duration</th>
                <th data-sort="created_at">Created</th>
            </tr>
        </thead>
        <tbody id="tasks-table-body"></tbody>
    </table>
    <div class="table-pagination">
        <button onclick="app.prevPage()">← Previous</button>
        <span id="page-info">Page 1 of 1</span>
        <button onclick="app.nextPage()">Next →</button>
    </div>
</section>
```

---

## 5. Feature 3: Cost Analytics Charts

### 5.1 Overview

Implement interactive cost visualization using **Chart.js**.

**Reference**: [Chart.js Dashboard Guide](https://embeddable.com/blog/how-to-build-dashboards-with-chart-js)

### 5.2 Integration

```html
<!-- Add Chart.js CDN to index.html -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

### 5.3 Analytics API Endpoints

```python
# api/analytics.py

@router.get("/costs/daily")
async def get_daily_costs(days: int = 30, db: AsyncSession = Depends(get_db_session)):
    """Get daily cost aggregation."""
    start_date = datetime.utcnow() - timedelta(days=days)
    query = select(
        func.date(TaskDB.created_at).label("date"),
        func.sum(TaskDB.cost_usd).label("total_cost"),
        func.count(TaskDB.task_id).label("task_count"),
    ).where(TaskDB.created_at >= start_date).group_by(func.date(TaskDB.created_at))
    
    result = await db.execute(query)
    rows = result.all()
    return {
        "dates": [str(r.date) for r in rows],
        "costs": [float(r.total_cost or 0) for r in rows],
        "task_counts": [int(r.task_count) for r in rows],
    }

@router.get("/costs/by-subagent")
async def get_costs_by_subagent(days: int = 30, db: AsyncSession = Depends(get_db_session)):
    """Get cost breakdown by subagent."""
    start_date = datetime.utcnow() - timedelta(days=days)
    query = select(
        TaskDB.assigned_agent,
        func.sum(TaskDB.cost_usd).label("total_cost"),
    ).where(TaskDB.created_at >= start_date).group_by(TaskDB.assigned_agent)
    
    result = await db.execute(query)
    rows = result.all()
    return {
        "subagents": [r.assigned_agent or "unknown" for r in rows],
        "costs": [float(r.total_cost or 0) for r in rows],
    }

@router.get("/summary")
async def get_analytics_summary(db: AsyncSession = Depends(get_db_session)):
    """Get overall analytics summary."""
    today = datetime.utcnow().date()
    
    # Today
    today_q = select(func.sum(TaskDB.cost_usd), func.count(TaskDB.task_id)).where(
        func.date(TaskDB.created_at) == today
    )
    today_r = (await db.execute(today_q)).one()
    
    # All time
    all_q = select(func.sum(TaskDB.cost_usd), func.count(TaskDB.task_id))
    all_r = (await db.execute(all_q)).one()
    
    return {
        "today_cost": float(today_r[0] or 0),
        "today_tasks": int(today_r[1] or 0),
        "total_cost": float(all_r[0] or 0),
        "total_tasks": int(all_r[1] or 0),
    }
```

### 5.4 Chart.js Implementation

```javascript
// app.js - Chart rendering

async loadDailyCostsChart() {
    const response = await fetch('/api/analytics/costs/daily?days=30');
    const data = await response.json();
    
    const ctx = document.getElementById('daily-costs-chart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [{
                label: 'Cost (USD)',
                data: data.costs,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { callback: (v) => `$${v.toFixed(2)}` }
                }
            }
        }
    });
}

async loadSubagentCostsChart() {
    const response = await fetch('/api/analytics/costs/by-subagent');
    const data = await response.json();
    
    const ctx = document.getElementById('subagent-costs-chart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.subagents,
            datasets: [{
                data: data.costs,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 206, 86, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                ]
            }]
        }
    });
}
```

---

## 6. Feature 4: Credential Management UI

### 6.1 Overview

**Critical Feature (P0)**: When Claude CLI credentials are missing, expired, or rate-limited, show a prominent banner with file upload capability.

**Reference**: [Claude Rate Limits](https://platform.claude.com/docs/en/api/rate-limits)

### 6.2 Credential Status API

```python
# api/credentials.py

from enum import Enum

class CredentialStatus(str, Enum):
    VALID = "valid"
    MISSING = "missing"
    EXPIRED = "expired"
    REFRESH_NEEDED = "refresh_needed"
    RATE_LIMITED = "rate_limited"
    CLI_UNAVAILABLE = "cli_unavailable"

router = APIRouter(prefix="/credentials", tags=["credentials"])

@router.get("/status")
async def get_credential_status() -> CredentialStatusResponse:
    """Check credential and CLI status."""
    
    # 1. Check if Claude CLI is available
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, timeout=5)
        cli_available = result.returncode == 0
        cli_version = result.stdout.decode().strip() if cli_available else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return CredentialStatusResponse(
            status=CredentialStatus.CLI_UNAVAILABLE,
            message="Claude CLI not found in container",
            cli_available=False,
        )
    
    # 2. Check if credentials file exists
    creds_path = settings.credentials_path
    if not creds_path.exists():
        return CredentialStatusResponse(
            status=CredentialStatus.MISSING,
            message="Credentials file not found. Please upload claude.json",
            cli_available=True, cli_version=cli_version,
        )
    
    # 3. Parse and validate credentials
    try:
        creds_data = json.loads(creds_path.read_text())
        creds = ClaudeCredentials(**creds_data)
        
        if creds.is_expired:
            return CredentialStatusResponse(
                status=CredentialStatus.EXPIRED,
                message="Credentials expired",
                cli_available=True, cli_version=cli_version,
            )
        
        if creds.needs_refresh:
            return CredentialStatusResponse(
                status=CredentialStatus.REFRESH_NEEDED,
                message="Credentials expiring soon",
                cli_available=True, cli_version=cli_version,
                expires_at=creds.expires_at_datetime.isoformat(),
            )
        
        return CredentialStatusResponse(
            status=CredentialStatus.VALID,
            message="Credentials valid",
            cli_available=True, cli_version=cli_version,
            expires_at=creds.expires_at_datetime.isoformat(),
        )
    except Exception as e:
        return CredentialStatusResponse(
            status=CredentialStatus.MISSING,
            message=f"Invalid credentials file: {str(e)}",
            cli_available=True, cli_version=cli_version,
        )
```

### 6.3 File Upload Endpoint

```python
# api/credentials.py - File upload (FastAPI)

from fastapi import File, UploadFile
import aiofiles

@router.post("/upload")
async def upload_credentials(
    file: UploadFile = File(..., description="claude.json credentials file")
) -> APIResponse:
    """Upload credentials file."""
    
    if not file.filename.endswith('.json'):
        raise HTTPException(400, "File must be a JSON file")
    
    content = await file.read()
    try:
        creds_data = json.loads(content)
        creds = ClaudeCredentials(**creds_data)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON file")
    except Exception as e:
        raise HTTPException(400, f"Invalid credentials format: {str(e)}")
    
    if creds.is_expired:
        raise HTTPException(400, "Credentials are already expired")
    
    # Save to persistent storage
    creds_path = settings.credentials_path
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(creds_path, 'wb') as f:
        await f.write(content)
    
    return APIResponse(
        success=True,
        message="Credentials uploaded successfully",
        data={"expires_at": creds.expires_at_datetime.isoformat()}
    )
```

### 6.4 UI: Credential Banner

```html
<!-- Credential Status Banner -->
<div id="credential-banner" class="credential-banner hidden">
    <div class="banner-content">
        <span class="banner-icon">⚠️</span>
        <span id="credential-message">Credentials required</span>
        <label class="upload-btn">
            Upload claude.json
            <input type="file" id="credential-file" accept=".json" hidden>
        </label>
    </div>
</div>
```

### 6.5 JavaScript: Credential Check

```javascript
async checkCredentialStatus() {
    const response = await fetch('/api/credentials/status');
    const data = await response.json();
    
    const banner = document.getElementById('credential-banner');
    const message = document.getElementById('credential-message');
    
    if (data.status === 'valid') {
        banner.classList.add('hidden');
        return;
    }
    
    banner.classList.remove('hidden');
    
    const messages = {
        'cli_unavailable': '❌ Claude CLI not available',
        'missing': '📁 Please upload claude.json',
        'expired': '⏰ Credentials expired',
        'refresh_needed': '⚠️ Credentials expiring soon',
        'rate_limited': '🚫 Rate limited'
    };
    message.textContent = messages[data.status] || data.message;
}
```

---

## 7. Feature 5: Skills/Subagent Folder Management

### 7.1 Overview

Allow users to upload and manage custom skills and subagent configurations.

### 7.2 Existing Paths (from `core/config.py`)

| Path | Purpose | Persistent |
|------|---------|------------|
| `/app/agents` | Built-in agents | ❌ Read-only |
| `/data/config/agents` | User agents | ✅ Yes |
| `/app/skills` | Built-in skills | ❌ Read-only |
| `/data/config/skills` | User skills | ✅ Yes |

### 7.3 Registry API

```python
# api/registry.py

@router.get("/skills")
async def list_skills() -> List[SkillInfo]:
    """List all skills (built-in + user)."""
    skills = []
    
    for skill_dir in settings.skills_dir.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skills.append(SkillInfo(name=skill_dir.name, is_builtin=True))
    
    if settings.user_skills_dir.exists():
        for skill_dir in settings.user_skills_dir.iterdir():
            if skill_dir.is_dir():
                skills.append(SkillInfo(name=skill_dir.name, is_builtin=False))
    
    return skills

@router.post("/skills/upload")
async def upload_skill(
    name: str = Form(...),
    files: List[UploadFile] = File(...)
) -> APIResponse:
    """Upload a new skill folder."""
    skill_dir = settings.user_skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    for file in files:
        file_path = skill_dir / file.filename
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(await file.read())
    
    return APIResponse(success=True, message=f"Skill '{name}' uploaded")

@router.delete("/skills/{name}")
async def delete_skill(name: str) -> APIResponse:
    """Delete a user skill."""
    skill_dir = settings.user_skills_dir / name
    if not skill_dir.exists():
        raise HTTPException(404, "Skill not found")
    
    shutil.rmtree(skill_dir)
    return APIResponse(success=True, message=f"Skill '{name}' deleted")
```

### 7.4 Skill Structure

```
/data/config/skills/my-skill/
├── SKILL.md           # Description
├── scripts/
│   ├── analyze.py     # Executable script
│   └── transform.sh   # Shell script
└── templates/
    └── output.md
```

---

## 8. Feature 6: Cloud Storage Integration

### 8.1 Overview

Support S3/PostgreSQL for enterprise deployments.

### 8.2 Configuration

```python
# core/config.py (existing)
storage_backend: str = "local"  # "local", "s3", "postgresql"
s3_bucket: str | None = None
s3_prefix: str = "claude-agent"
```

### 8.3 Storage Abstraction

```python
# core/storage/base.py

from abc import ABC, abstractmethod

class StorageBackend(ABC):
    @abstractmethod
    async def read(self, key: str) -> bytes: pass
    
    @abstractmethod
    async def write(self, key: str, data: bytes) -> None: pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool: pass

# core/storage/s3.py

import aioboto3

class S3Storage(StorageBackend):
    def __init__(self, bucket: str, prefix: str):
        self.bucket = bucket
        self.prefix = prefix
        self.session = aioboto3.Session()
    
    async def read(self, key: str) -> bytes:
        async with self.session.client('s3') as s3:
            response = await s3.get_object(Bucket=self.bucket, Key=f"{self.prefix}/{key}")
            return await response['Body'].read()
    
    async def write(self, key: str, data: bytes) -> None:
        async with self.session.client('s3') as s3:
            await s3.put_object(Bucket=self.bucket, Key=f"{self.prefix}/{key}", Body=data)
```

---

## 9. Implementation Timeline

| Phase | Features | Duration |
|-------|----------|----------|
| **Phase 1** | Credential status API, upload endpoint, banner UI | Week 1-2 |
| **Phase 2** | Task table API, pagination, Chart.js integration | Week 3-4 |
| **Phase 3** | Subagent logs DB model, capture, viewer UI | Week 5-6 |
| **Phase 4** | Skills registry, S3 storage backend | Week 7-8 |

---

## 10. Technical Dependencies

### Python Packages

```txt
python-multipart>=0.0.6    # File uploads
aiofiles>=23.0.0           # Async file I/O
aioboto3>=12.0.0           # S3 async client (optional)
```

### Frontend

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

### Database Migration

```python
# Add SubagentLogDB table
op.create_table('subagent_logs',
    sa.Column('id', sa.Integer(), primary_key=True),
    sa.Column('task_id', sa.String(255), sa.ForeignKey('tasks.task_id')),
    sa.Column('trace_id', sa.String(64), index=True),
    sa.Column('subagent_name', sa.String(255)),
    sa.Column('cost_usd', sa.Float()),
    sa.Column('status', sa.String(50)),
)
```

---

## Appendix: API Route Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/credentials/status` | GET | Check credential/CLI status |
| `/api/credentials/upload` | POST | Upload credentials file |
| `/api/tasks/table` | GET | Paginated task table |
| `/api/analytics/summary` | GET | Cost summary |
| `/api/analytics/costs/daily` | GET | Daily costs |
| `/api/analytics/costs/by-subagent` | GET | Costs by subagent |
| `/api/tasks/{id}/logs` | GET | Subagent logs |
| `/api/registry/skills` | GET/POST/DELETE | Skills management |
| `/api/registry/agents` | GET | List agents |
