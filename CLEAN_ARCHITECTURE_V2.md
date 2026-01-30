# Clean Architecture V2 - Based on claude-code-agent Success Patterns

## What We Learned from claude-code-agent

### ✅ **Patterns That Work in Production**

1. **Monorepo with Clear Layers** (NOT microservices)
2. **No sys.path hacks** - Clean absolute imports
3. **No duplicate nesting** - `core/database/models.py` NOT `core/database/database/models.py`
4. **Modular providers** - Copy-paste pattern for new integrations
5. **Single source of truth** - One models file, one config, explicit exports
6. **Pydantic everywhere** - Request/response/config/domain models
7. **Dependency injection** - FastAPI Depends() for sessions
8. **Structured logging** - `structlog` with context

---

## Proposed Clean Architecture (Based on Working System)

```
agent-bot/                           # Root (single Python project)
├── main.py                          # FastAPI entry point + lifespan
├── pyproject.toml                   # Single project config
├── .env                             # Environment variables
│
├── api/                             # Routes Layer (HTTP handlers)
│   ├── __init__.py                  # Export routers
│   ├── health.py                    # Health checks
│   ├── oauth.py                     # OAuth endpoints
│   ├── tasks.py                     # Task API
│   ├── analytics.py                 # Analytics endpoints
│   ├── conversations.py             # Conversation API
│   └── webhooks/                    # Webhook providers (modular)
│       ├── __init__.py
│       ├── common/                  # Shared webhook utilities
│       │   ├── validation.py
│       │   └── utils.py
│       ├── github/                  # GitHub provider
│       │   ├── __init__.py          # Export router
│       │   ├── routes.py            # HTTP handler
│       │   ├── handlers.py          # Business logic
│       │   ├── models.py            # GitHub-specific models
│       │   └── validation.py        # HMAC validation
│       ├── jira/                    # Jira provider (same structure)
│       ├── slack/                   # Slack provider (same structure)
│       └── sentry/                  # Sentry provider (same structure)
│
├── core/                            # Service Layer (business logic)
│   ├── __init__.py                  # Export key services
│   ├── config.py                    # Pydantic Settings (singleton)
│   ├── logging_config.py            # Structlog configuration
│   │
│   ├── clients/                     # External API clients
│   │   ├── __init__.py
│   │   ├── github_client.py         # GitHub MCP client
│   │   ├── jira_client.py           # Jira MCP client
│   │   └── slack_client.py          # Slack MCP client
│   │
│   ├── services/                    # Business services
│   │   ├── __init__.py
│   │   ├── token_service.py         # Token management
│   │   ├── conversation_service.py  # Conversation manager
│   │   ├── analytics_service.py     # Cost tracking
│   │   └── agent_service.py         # Agent orchestration
│   │
│   ├── agents/                      # Agent implementations
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseAgent
│   │   ├── brain.py                 # Orchestrator
│   │   ├── executor.py              # CLI executor
│   │   └── workflows/               # Workflow agents
│   │       ├── github_workflow.py
│   │       ├── jira_workflow.py
│   │       └── slack_workflow.py
│   │
│   ├── database/                    # Data layer
│   │   ├── __init__.py              # Export engine, session_factory, get_session
│   │   ├── models.py                # SQLAlchemy ORM (ALL models in ONE file)
│   │   └── redis_client.py          # Redis queue/cache
│   │
│   └── utils/                       # Utilities
│       ├── cli_runner.py            # Claude CLI wrapper
│       ├── repo_manager.py          # Git operations
│       └── webhook_engine.py        # Webhook processing
│
├── shared/                          # Domain Models (Pydantic)
│   ├── __init__.py                  # Explicit exports with __all__
│   └── models.py                    # ALL Pydantic models
│       ├── Enums: TaskStatus, TaskPriority, Platform
│       ├── Task, Installation, Conversation, Message
│       ├── AgentTask, AgentResult
│       ├── APIResponse (standard wrapper)
│       └── Request/Response models
│
├── workers/                         # Background processors
│   ├── __init__.py
│   └── task_worker.py               # Async queue consumer
│
├── tests/                           # All tests centralized
│   ├── conftest.py                  # Fixtures
│   ├── unit/                        # Unit tests
│   │   ├── api/
│   │   ├── core/
│   │   └── shared/
│   ├── integration/                 # Integration tests
│   └── e2e/                         # End-to-end tests
│
└── migrations/                      # Database migrations
    ├── env.py
    └── versions/
        ├── 001_create_installations.sql
        ├── 002_create_tasks.sql
        ├── 003_create_analytics.sql
        └── 004_create_conversations.sql
```

---

## Key Improvements Over Current Architecture

### 1. **No Duplicate Nesting** ✅

**BEFORE (BAD):**
```
integrations/token_service/token_service/service.py  ← Duplicate!
agent-container/token_service/token_service/models.py  ← Duplicate!
```

**AFTER (GOOD):**
```
core/services/token_service.py  ← Clean!
shared/models.py  ← All models in ONE file!
```

### 2. **No sys.path Hacks** ✅

**BEFORE (BAD):**
```python
sys.path.insert(0, str(Path(__file__).parent.parent))  # 🤮
```

**AFTER (GOOD):**
```python
from core.config import settings
from shared import Task, TaskStatus
from api.webhooks.github import router
```

Proper `pyproject.toml`:
```toml
[project]
name = "agent-bot"
version = "2.0.0"

[tool.setuptools]
packages = ["api", "core", "shared", "workers"]
```

### 3. **No Code Duplication** ✅

**BEFORE (BAD):**
```python
# main.py - 123 lines duplicated
class RedisQueueAdapter:  # 36 lines
class PostgresInstallationRepository:  # 87 lines
```

**AFTER (GOOD):**
```python
# main.py - Clean imports
from core.database import RedisQueueAdapter
from core.database import PostgresInstallationRepository
```

### 4. **Single Models File** ✅

**BEFORE (SCATTERED):**
```
agent-container/core/agents/models.py
api-gateway/api/analytics/models.py
api-gateway/api/conversations/models.py
integrations/token_service/token_service/models.py
```

**AFTER (CENTRALIZED):**
```
shared/models.py  ← ALL models here (like claude-code-agent)
```

**Why:** 
- One source of truth
- Easy to find models
- No circular imports
- Easier to maintain

### 5. **Modular Webhook Providers** ✅

**Pattern from claude-code-agent:**
```
api/webhooks/
├── common/           # Shared utilities
├── github/           # Complete module
│   ├── routes.py     # HTTP handler
│   ├── handlers.py   # Business logic
│   ├── models.py     # Provider models
│   └── validation.py # HMAC validation
├── jira/             # Copy github structure
└── slack/            # Copy github structure
```

**To add new provider:** Copy `github/` folder, change provider name, done!

### 6. **Clean Layering** ✅

```
main.py (FastAPI app)
    ↓ includes
api/*.py (Routes)
    ↓ calls
core/services/*.py (Business logic)
    ↓ uses
core/database/models.py (Data layer)
    ↓ uses
shared/models.py (Domain models)
```

**No circular dependencies possible** - Each layer only depends on layers below.

### 7. **Explicit Exports** ✅

**shared/__init__.py:**
```python
from .models import (
    Task,
    TaskStatus,
    TaskPriority,
    Installation,
    Platform,
    Conversation,
    Message,
    AgentTask,
    AgentResult,
    APIResponse,
)

__all__ = [
    "Task",
    "TaskStatus",
    "TaskPriority",
    "Installation",
    "Platform",
    "Conversation",
    "Message",
    "AgentTask",
    "AgentResult",
    "APIResponse",
]
```

**Usage:**
```python
from shared import Task, TaskStatus, APIResponse  # Clean!
```

### 8. **Dependency Injection** ✅

**core/database/__init__.py:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(settings.database_url)
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session():
    async with async_session_maker() as session:
        yield session
```

**api/tasks.py:**
```python
from core.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

@router.get("/tasks")
async def list_tasks(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(TaskDB))
    return result.scalars().all()
```

---

## Migration from Current Structure

### Phase 1: Flatten Folder Structure (2 hours)

```bash
# 1. Create new structure
mkdir -p agent-bot/{api,core,shared,workers,tests,migrations}
mkdir -p agent-bot/core/{clients,services,agents,database,utils}
mkdir -p agent-bot/api/webhooks/{common,github,jira,slack,sentry}

# 2. Move files (no duplicates)
# Token service
mv integrations/token_service/token_service/service.py core/services/token_service.py
mv integrations/token_service/token_service/models.py shared/models.py  # Merge here

# Agents
mv agent-container/core/agents/* core/agents/

# Webhooks
mv api-gateway/webhooks/handlers/github.py api/webhooks/github/handlers.py
mv api-gateway/webhooks/handlers/jira.py api/webhooks/jira/handlers.py
mv api-gateway/webhooks/handlers/slack.py api/webhooks/slack/handlers.py

# Database
mv agent-container/adapters/database/postgres_installation_repository.py \
   core/database/repositories.py

# MCP Clients
mv agent-container/core/mcp_clients/* core/clients/

# Workers
mv agent-container/workers/task_worker.py workers/task_worker.py

# 3. Delete empty/duplicate folders
rm -rf integrations/token_service/token_service/
rm -rf agent-container/token_service/
```

### Phase 2: Fix All Imports (2 hours)

```bash
# Replace duplicate imports
find agent-bot -name "*.py" -exec sed -i \
  's/from token_service.token_service/from core.services.token_service/g' {} \;

find agent-bot -name "*.py" -exec sed -i \
  's/from core.agents.models/from shared.models/g' {} \;

# Remove sys.path hacks
find agent-bot -name "*.py" -exec sed -i \
  '/sys.path.insert/d' {} \;
```

### Phase 3: Consolidate Models (1 hour)

**Create shared/models.py:**
```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

# Enums
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Platform(str, Enum):
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    SENTRY = "sentry"

# Domain Models
class Installation(BaseModel):
    id: str
    platform: Platform
    organization_id: str
    # ... all fields

class Task(BaseModel):
    task_id: str
    installation_id: str
    status: TaskStatus
    # ... all fields

# ... All other models here
```

### Phase 4: Remove Duplicated Code in main.py (1 hour)

**BEFORE:**
```python
# Lines 41-166: Duplicated classes
class RedisQueueAdapter: ...
class PostgresInstallationRepository: ...
```

**AFTER:**
```python
from core.database import RedisQueueAdapter, PostgresInstallationRepository

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = await redis.from_url(redis_url)
    db_pool = await asyncpg.create_pool(database_url)
    
    app.state.queue = RedisQueueAdapter(redis_client)
    app.state.repository = PostgresInstallationRepository(db_pool)
    
    yield
    
    await redis_client.close()
    await db_pool.close()
```

### Phase 5: Create pyproject.toml (1 hour)

**Single project configuration:**
```toml
[project]
name = "agent-bot"
version = "2.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "pydantic>=2.6.0",
    "redis>=5.0.0",
    "asyncpg>=0.29.0",
    "structlog>=24.1.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "mypy>=1.8.0",
    "ruff>=0.2.0",
]

[tool.setuptools]
packages = ["api", "core", "shared", "workers"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.mypy]
strict = true
```

### Phase 6: Update main.py (1 hour)

**Clean main.py:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import init_db, RedisQueueAdapter, PostgresInstallationRepository
from api import oauth, webhooks, tasks, analytics, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    redis_client = await RedisQueueAdapter.create(settings.redis_url)
    db_pool = await PostgresInstallationRepository.create_pool(settings.database_url)
    
    app.state.redis_client = redis_client
    app.state.db_pool = db_pool
    
    yield
    
    await redis_client.close()
    await db_pool.close()

app = FastAPI(
    title="Agent Bot",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router, tags=["health"])
app.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
```

---

## Final Structure Comparison

| Issue | BEFORE | AFTER | Improvement |
|-------|--------|-------|-------------|
| Duplicate nesting | ❌ Yes (3 places) | ✅ No | Clean imports |
| sys.path hacks | ❌ 2 hacks | ✅ 0 hacks | Proper packaging |
| Code duplication | ❌ 123 lines | ✅ 0 lines | DRY principle |
| Max nesting | ❌ 6 levels | ✅ 3 levels | 50% reduction |
| Models scattered | ❌ 4+ files | ✅ 1 file | Single source |
| Import clarity | ❌ Confusing | ✅ Clear | Better DX |
| Production ready | ❌ No | ✅ Yes | Deployable |

---

## Estimated Effort

- **Phase 1-3:** 5 hours (restructure + imports + models)
- **Phase 4-6:** 3 hours (dedupe + config + main.py)
- **Total:** 8 hours with one engineer
- **Risk:** LOW (mostly file moves)
- **Impact:** HIGH (production-ready structure)

---

## Success Criteria

After refactor, you should be able to:

✅ `python -m main` - Starts without import errors
✅ `pytest` - All tests pass
✅ `mypy .` - No type errors
✅ `from shared import Task` - Clean imports work
✅ `docker-compose up` - Starts successfully
✅ No sys.path manipulation anywhere
✅ No duplicate code
✅ All files < 300 lines
✅ New developers can navigate easily

---

## Decision

**DO THE REFACTOR NOW**

**Why:**
1. Based on proven patterns (claude-code-agent has been running in production)
2. Fixes all architectural issues
3. 8 hours is small investment
4. Makes adding new providers trivial (copy-paste pattern)
5. Future developers will thank you

**When:**
- **NOW** - Before adding more features
- **NOW** - Before expanding team
- **NOW** - Before production deployment

The claude-code-agent architecture has proven itself. Let's copy what works.
