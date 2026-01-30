# Architecture Refactor Proposal - Critical Issues Fixed

## Current Problems

1. ❌ Duplicate folder nesting (token_service/token_service/)
2. ❌ Code duplication (123 lines in main.py)
3. ❌ sys.path hacks (broken imports)
4. ❌ Inconsistent naming (kebab + snake mix)
5. ❌ Too deep nesting (6 levels)
6. ❌ Unclear responsibilities
7. ❌ Redundant naming (api/api/)

---

## Proposed Clean Structure

```
agents-system/
├── services/                    # Deployable services
│   ├── gateway/                 # API Gateway service
│   │   ├── main.py             # FastAPI app
│   │   ├── routers/            # API routes
│   │   │   ├── webhooks.py     # Webhook endpoints
│   │   │   ├── oauth.py        # OAuth endpoints
│   │   │   └── health.py       # Health/metrics
│   │   ├── middleware/         # CORS, auth, etc
│   │   └── Dockerfile
│   │
│   └── worker/                  # Task worker service
│       ├── main.py             # Worker loop
│       ├── processor.py        # Task processing
│       ├── Dockerfile
│       └── config.py
│
├── domain/                      # Business logic (pure Python)
│   ├── models/                 # Pydantic models
│   │   ├── task.py
│   │   ├── installation.py
│   │   ├── conversation.py
│   │   └── agent.py
│   │
│   ├── agents/                 # Agent implementations
│   │   ├── base.py            # BaseAgent
│   │   ├── brain.py           # Orchestrator
│   │   ├── executor.py        # CLI executor
│   │   └── workflows/         # Specialized workflows
│   │       ├── github.py
│   │       ├── jira.py
│   │       └── slack.py
│   │
│   └── services/              # Business services
│       ├── token_service.py   # Token management
│       ├── conversation.py    # Conversation manager
│       └── analytics.py       # Analytics tracker
│
├── infrastructure/             # External integrations
│   ├── ports/                 # Interfaces (protocols)
│   │   ├── queue.py
│   │   ├── database.py
│   │   ├── cache.py
│   │   └── cli.py
│   │
│   ├── adapters/              # Implementations
│   │   ├── queue/
│   │   │   ├── redis.py
│   │   │   └── memory.py
│   │   ├── database/
│   │   │   ├── postgres.py
│   │   │   └── sqlite.py
│   │   ├── cli/
│   │   │   ├── claude.py
│   │   │   └── mock.py
│   │   └── mcp/
│   │       ├── github.py
│   │       ├── jira.py
│   │       └── slack.py
│   │
│   └── webhooks/              # Webhook handlers
│       ├── registry.py
│       └── handlers/
│           ├── github.py
│           ├── jira.py
│           ├── slack.py
│           └── sentry.py
│
├── database/                   # Database layer
│   ├── migrations/
│   │   └── versions/
│   │       ├── 001_installations.sql
│   │       ├── 002_tasks.sql
│   │       ├── 003_analytics.sql
│   │       └── 004_conversations.sql
│   └── connection.py
│
├── tests/                      # All tests in one place
│   ├── unit/
│   │   ├── domain/
│   │   ├── infrastructure/
│   │   └── services/
│   ├── integration/
│   └── e2e/
│
├── docker-compose.yml
├── pyproject.toml             # Single Python project
└── README.md
```

---

## Key Improvements

### 1. **Clear Separation of Concerns**

| Layer | Responsibility | Dependencies |
|-------|----------------|--------------|
| **services/** | HTTP/Workers (entry points) | → domain, infrastructure |
| **domain/** | Business logic (pure Python) | → NONE (pure) |
| **infrastructure/** | External systems | → domain/ports |

### 2. **No Duplicate Nesting**

**Before:**
```
integrations/token_service/token_service/service.py
```

**After:**
```
domain/services/token_service.py
```

### 3. **No sys.path Hacks**

**Before:**
```python
sys.path.insert(0, ...)  # 🤮
```

**After:**
```python
from domain.services.token_service import TokenService  # ✅
```

Proper Python package with `pyproject.toml`:
```toml
[project]
name = "agent-bot"
version = "2.0.0"

[tool.setuptools.packages.find]
where = ["."]
include = ["domain*", "infrastructure*", "services*"]
```

### 4. **Consistent Naming**

- Services: `kebab-case` (gateway, worker)
- Python modules: `snake_case` (token_service.py)
- Classes: `PascalCase` (TokenService)

### 5. **Reduced Nesting**

**Before:**
```
agent-bot/agent-container/core/agents/workflows/github_handler.py (6 levels)
```

**After:**
```
domain/agents/workflows/github.py (3 levels)
```

### 6. **Single Source of Truth**

**Before:**
- RedisQueueAdapter in main.py (inline)
- RedisQueueAdapter in adapters/ (separate)
- PostgresRepository in main.py (inline)
- PostgresRepository in adapters/ (separate)

**After:**
- ONE RedisQueueAdapter in `infrastructure/adapters/queue/redis.py`
- Import everywhere else

### 7. **Clear Imports**

**Before:**
```python
from token_service.token_service.service import TokenService  # 🤮
from core.agents.workflows.github_handler import ...  # 🤮
```

**After:**
```python
from domain.services.token_service import TokenService  # ✅
from domain.agents.workflows.github import GitHubWorkflow  # ✅
```

---

## Migration Path

### Phase 1: Restructure Packages (2-3 hours)

```bash
# Create new structure
mkdir -p domain/{models,agents,services}
mkdir -p infrastructure/{ports,adapters,webhooks}
mkdir -p services/{gateway,worker}

# Move files (no code changes yet)
mv agent-container/token_service/token_service/* domain/services/
mv agent-container/core/agents/* domain/agents/
mv agent-container/adapters/* infrastructure/adapters/
mv api-gateway/webhooks/handlers/* infrastructure/webhooks/handlers/

# Remove duplicates
rm -rf agent-container/token_service/token_service/
```

### Phase 2: Fix Imports (2-3 hours)

```bash
# Find and replace imports
find . -name "*.py" -exec sed -i \
  's/from token_service.token_service/from domain.services.token_service/g' {} \;

find . -name "*.py" -exec sed -i \
  's/from core.agents/from domain.agents/g' {} \;
```

### Phase 3: Remove Duplication (1-2 hours)

```python
# services/gateway/main.py - BEFORE
class RedisQueueAdapter:  # 36 lines inline
    ...

class PostgresInstallationRepository:  # 87 lines inline
    ...

# services/gateway/main.py - AFTER
from infrastructure.adapters.queue.redis import RedisQueueAdapter
from infrastructure.adapters.database.postgres import PostgresInstallationRepository
```

### Phase 4: Remove sys.path Hacks (1 hour)

```python
# BEFORE
sys.path.insert(0, ...)

# AFTER
# Use proper package imports with pyproject.toml
```

### Phase 5: Update Tests (1-2 hours)

```bash
# Consolidate tests
mv agent-bot/tests/* tests/integration/
mv agent-container/tests/* tests/unit/infrastructure/
mv api-gateway/tests/* tests/unit/services/
```

### Phase 6: Single pyproject.toml (1 hour)

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
    # ... all deps
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "mypy>=1.8.0",
    "ruff>=0.2.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["domain*", "infrastructure*", "services*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

---

## Benefits After Refactor

| Issue | Before | After | Improvement |
|-------|--------|-------|-------------|
| Duplicate nesting | ❌ Yes | ✅ No | Clean imports |
| Code duplication | ❌ 123 lines | ✅ 0 lines | DRY |
| sys.path hacks | ❌ 2 hacks | ✅ 0 hacks | Proper packaging |
| Max nesting depth | ❌ 6 levels | ✅ 3 levels | 50% reduction |
| Import clarity | ❌ Confusing | ✅ Clear | Better DX |
| Test organization | ❌ Scattered | ✅ Centralized | Easier to run |
| Package structure | ❌ Broken | ✅ Standard | Production-ready |

---

## Estimated Effort

- **Phase 1-3:** 6-8 hours (restructure + fix imports + dedupe)
- **Phase 4-6:** 3-4 hours (cleanup + tests + packaging)
- **Total:** 10-12 hours with ONE engineer
- **Risk:** LOW (mostly file moves, minimal code changes)
- **Impact:** HIGH (much cleaner, maintainable codebase)

---

## Decision

**Recommendation: DO THE REFACTOR**

**Why:**
1. Current structure is a maintenance nightmare
2. Won't scale as team grows
3. Confusing for new developers
4. Production deployments will have issues
5. 10-12 hours is a small investment
6. Clean architecture pays dividends long-term

**When:**
- Before adding more features
- Before expanding team
- Before production deployment
- **NOW** (technical debt compounds)

---

## Alternative: Live With Current Issues

**If you don't refactor:**

**Costs:**
- Developers spend 15-20% more time navigating code
- New team members take 2-3x longer to onboard
- Bug risk increases (duplicate code, sys.path issues)
- Deployment complexity increases
- Technical debt accumulates

**Benefits:**
- Save 10-12 hours now
- No immediate disruption

**Verdict:** **NOT worth it** - refactor is small effort, huge benefit
