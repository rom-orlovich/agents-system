# TDD Implementation Plan: Agent Bot Feature Expansion

## Overview

This document outlines a comprehensive Test-Driven Development plan for:
1. Porting Claude Code Agent features to Agent Bot dashboards (internal + external)
2. OAuth integration button in external dashboard
3. Environment variable consolidation
4. Makefile cleanup and script organization
5. ChromaDB integration as knowledge graph

---

## Phase 1: Environment Variable Consolidation

### 1.1 Current State Analysis

**Files Found:**
```
agent-bot/.env.example                          (ROOT - 106 lines)
agent-bot/agent-engine/.env.example             (Service-specific)
agent-bot/api-gateway/.env.example              (Service-specific)
agent-bot/dashboard-api/.env.example            (Service-specific)
agent-bot/oauth-service/.env.example            (Service-specific)
agent-bot/api-services/github-api/.env.example  (Service-specific)
agent-bot/api-services/jira-api/.env.example    (Service-specific)
agent-bot/api-services/slack-api/.env.example   (Service-specific)
agent-bot/api-services/sentry-api/.env.example  (Service-specific)
agent-bot/mcp-servers/jira-mcp/.env.example     (Service-specific)
agent-bot/mcp-servers/slack-mcp/.env.example    (Service-specific)
agent-bot/mcp-servers/sentry-mcp/.env.example   (Service-specific)
```

### 1.2 Variable Classification

| Variable Category | Root .env | Service-Specific | Redundant? |
|------------------|-----------|------------------|------------|
| **CLI_PROVIDER** | ✅ | agent-engine | No - single source |
| **MAX_CONCURRENT_TASKS** | ✅ | agent-engine | Yes - duplicate |
| **POSTGRES_*** | ✅ | dashboard-api | Yes - use DATABASE_URL |
| **GITHUB_TOKEN** | ✅ | github-api | Yes - duplicate |
| **JIRA_URL/EMAIL/TOKEN** | ✅ | jira-api | Yes - duplicate |
| **SLACK_BOT_TOKEN** | ✅ | slack-api | Yes - duplicate |
| **SENTRY_AUTH_TOKEN** | ✅ | sentry-api | Yes - duplicate |
| **WEBHOOK_SECRETS** | ✅ | api-gateway | Yes - duplicate |
| **OAuth Credentials** | ✅ | oauth-service | Yes - duplicate |
| **MCP API URLs** | ❌ | mcp-servers | No - internal refs |

### 1.3 Recommended Structure

**Root `.env.example` (Single Source of Truth):**
```bash
# ============================================
# CORE CONFIGURATION
# ============================================
CLI_PROVIDER=claude
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT_SECONDS=3600
LOG_LEVEL=INFO
BASE_URL=https://yourdomain.com

# ============================================
# DATABASE
# ============================================
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
REDIS_URL=redis://redis:6379/0

# ============================================
# EXTERNAL API CREDENTIALS
# ============================================
# GitHub
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_WEBHOOK_SECRET=xxx

# Jira
JIRA_URL=https://company.atlassian.net
JIRA_EMAIL=agent@company.com
JIRA_API_TOKEN=xxxxxxxxxxxx
JIRA_WEBHOOK_SECRET=xxx

# Slack
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_SIGNING_SECRET=xxx

# Sentry
SENTRY_AUTH_TOKEN=xxxxxxxxxxxx
SENTRY_ORG_SLUG=your-org-slug
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_CLIENT_SECRET=xxx

# ============================================
# LLM PROVIDERS
# ============================================
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
CURSOR_API_KEY=cur_xxxxxxxxxxxx

# Claude Models
CLAUDE_MODEL_COMPLEX=opus
CLAUDE_MODEL_EXECUTION=sonnet

# Cursor Models
CURSOR_MODEL_COMPLEX=claude-sonnet-4.5
CURSOR_MODEL_EXECUTION=composer-1

# ============================================
# OAUTH (Multi-Tenant)
# ============================================
# GitHub App
GITHUB_APP_ID=123456
GITHUB_APP_NAME=my-agent-bot
GITHUB_CLIENT_ID=Iv1.abc123
GITHUB_CLIENT_SECRET=xxx
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"

# Slack App
SLACK_CLIENT_ID=123456789.123456789
SLACK_CLIENT_SECRET=xxx
SLACK_STATE_SECRET=xxx

# Jira OAuth
JIRA_CLIENT_ID=xxx
JIRA_CLIENT_SECRET=xxx

# Encryption
TOKEN_ENCRYPTION_KEY=xxx

# ============================================
# FEATURE FLAGS
# ============================================
CLAUDE_CODE_ENABLE_TASKS=true
ENABLE_KNOWLEDGE_GRAPH=false

# ============================================
# CHROMADB (Knowledge Graph)
# ============================================
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_COLLECTION=agent_knowledge
```

### 1.4 TDD Tasks for Environment Consolidation

```
□ TEST: scripts/validate-env.sh validates all required vars exist
□ TEST: docker-compose.yml correctly passes root .env to all services
□ TEST: Each service reads vars from environment (not local .env)
□ IMPL: Create scripts/validate-env.sh
□ IMPL: Update docker-compose.yml env_file references
□ IMPL: Remove service-specific .env.example files (except internal URLs)
□ IMPL: Create consolidated .env.example
```

---

## Phase 2: Makefile Cleanup & Script Organization

### 2.1 Current Issues

1. **Inline bash logic** - Complex shell commands embedded in Makefile
2. **Duplication** - cli-claude and cli-cursor have 90% same code
3. **Missing targets** - No oauth-service, no chromadb
4. **Inconsistent testing** - Different PYTHONPATH for each service

### 2.2 Proposed Script Structure

```
agent-bot/
├── scripts/
│   ├── cli/
│   │   ├── start.sh          # Start CLI (provider arg)
│   │   ├── stop.sh           # Stop CLI
│   │   └── logs.sh           # View CLI logs
│   ├── services/
│   │   ├── start.sh          # Start all services
│   │   ├── stop.sh           # Stop all services
│   │   ├── health.sh         # Health check all
│   │   └── logs.sh           # View service logs
│   ├── test/
│   │   ├── run-all.sh        # Run all tests
│   │   ├── run-unit.sh       # Run unit tests only
│   │   ├── run-integration.sh # Run integration tests
│   │   └── coverage.sh       # Generate coverage
│   ├── db/
│   │   ├── migrate.sh        # Create migration
│   │   ├── upgrade.sh        # Apply migrations
│   │   └── reset.sh          # Reset database
│   ├── env/
│   │   ├── validate.sh       # Validate .env
│   │   └── generate-key.sh   # Generate encryption keys
│   └── utils/
│       ├── clean.sh          # Clean caches
│       └── format.sh         # Format code
└── Makefile                   # Thin wrapper calling scripts
```

### 2.3 Proposed Makefile (Simplified)

```makefile
.PHONY: help init up down cli test lint format clean

SHELL := /bin/bash
PROVIDER ?= claude
SCALE ?= 1

# ============================================
# HELP
# ============================================
help:
	@./scripts/utils/help.sh

# ============================================
# INITIALIZATION
# ============================================
init:
	@./scripts/env/validate.sh || cp .env.example .env
	@pip install -e "agent-engine-package[dev]"
	@echo "✅ Initialized. Update .env with your credentials."

# ============================================
# SERVICES
# ============================================
up:
	@./scripts/services/start.sh

down:
	@./scripts/services/stop.sh

health:
	@./scripts/services/health.sh

logs:
	@./scripts/services/logs.sh $(SERVICE)

# ============================================
# CLI AGENTS
# ============================================
cli:
	@./scripts/cli/start.sh $(PROVIDER) $(SCALE)

cli-down:
	@./scripts/cli/stop.sh $(PROVIDER)

cli-logs:
	@./scripts/cli/logs.sh $(PROVIDER)

# Convenience aliases
cli-claude: PROVIDER=claude
cli-claude: cli

cli-cursor: PROVIDER=cursor
cli-cursor: cli

# ============================================
# TESTING
# ============================================
test:
	@./scripts/test/run-all.sh

test-unit:
	@./scripts/test/run-unit.sh

test-cov:
	@./scripts/test/coverage.sh

# Service-specific tests
test-%:
	@./scripts/test/run-service.sh $*

# ============================================
# CODE QUALITY
# ============================================
lint:
	@uv run ruff check .

format:
	@uv run ruff format .

# ============================================
# DATABASE
# ============================================
db-migrate:
	@./scripts/db/migrate.sh "$(MSG)"

db-upgrade:
	@./scripts/db/upgrade.sh

db-reset:
	@./scripts/db/reset.sh

# ============================================
# CLEANUP
# ============================================
clean:
	@./scripts/utils/clean.sh
```

### 2.4 TDD Tasks for Makefile

```
□ TEST: make help displays all commands correctly
□ TEST: make cli PROVIDER=claude starts Claude CLI
□ TEST: make cli PROVIDER=cursor starts Cursor CLI
□ TEST: make test runs all service tests
□ TEST: make health checks all services
□ IMPL: Create scripts/cli/start.sh
□ IMPL: Create scripts/cli/stop.sh
□ IMPL: Create scripts/services/start.sh
□ IMPL: Create scripts/services/health.sh
□ IMPL: Create scripts/test/run-all.sh
□ IMPL: Update Makefile to call scripts
□ IMPL: Remove inline bash from Makefile
```

---

## Phase 3: ChromaDB Integration

### 3.1 Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Agent Engine   │────▶│ Knowledge Graph │
│  (Task Worker)  │     │      MCP        │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │    ChromaDB     │
                        │   (Vector DB)   │
                        └─────────────────┘
```

### 3.2 Docker Configuration

**docker-compose.yml additions:**
```yaml
services:
  chromadb:
    image: chromadb/chroma:0.4.22
    container_name: agent-chromadb
    ports:
      - "8001:8000"  # 8000 used by api-gateway
    volumes:
      - chroma-data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3

  knowledge-graph-mcp:
    build: ./mcp-servers/knowledge-graph-mcp
    container_name: knowledge-graph-mcp
    depends_on:
      chromadb:
        condition: service_healthy
    environment:
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
      - CHROMA_COLLECTION=${CHROMA_COLLECTION:-agent_knowledge}
    networks:
      - agent-network

volumes:
  chroma-data:
```

### 3.3 Knowledge Graph MCP Server

**Directory Structure:**
```
mcp-servers/knowledge-graph-mcp/
├── __init__.py
├── main.py
├── server.py
├── tools/
│   ├── __init__.py
│   ├── store.py      # Store knowledge
│   ├── query.py      # Query knowledge
│   └── manage.py     # Collection management
├── models.py
├── config.py
├── requirements.txt
├── Dockerfile
├── .env.example
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_store.py
    ├── test_query.py
    └── test_manage.py
```

### 3.4 MCP Tool Definitions

```python
# tools/store.py
@mcp_tool(
    name="knowledge_store",
    description="Store knowledge in the vector database"
)
async def store_knowledge(
    content: str,
    metadata: dict[str, str],
    collection: str = "default"
) -> dict[str, str]:
    """Store a piece of knowledge with metadata."""
    ...

# tools/query.py
@mcp_tool(
    name="knowledge_query",
    description="Query similar knowledge from vector database"
)
async def query_knowledge(
    query: str,
    n_results: int = 5,
    collection: str = "default",
    filter_metadata: dict[str, str] | None = None
) -> list[dict]:
    """Query for similar knowledge."""
    ...

# tools/manage.py
@mcp_tool(
    name="knowledge_collections",
    description="List or manage knowledge collections"
)
async def manage_collections(
    action: Literal["list", "create", "delete"],
    collection: str | None = None
) -> dict:
    """Manage knowledge collections."""
    ...
```

### 3.5 TDD Tasks for ChromaDB

```
□ TEST: ChromaDB container starts and passes healthcheck
□ TEST: knowledge_store tool stores document with embeddings
□ TEST: knowledge_query returns similar documents
□ TEST: knowledge_collections lists all collections
□ TEST: Agent can use knowledge tools via MCP
□ IMPL: Add ChromaDB to docker-compose.yml
□ IMPL: Create knowledge-graph-mcp/server.py
□ IMPL: Create knowledge-graph-mcp/tools/store.py
□ IMPL: Create knowledge-graph-mcp/tools/query.py
□ IMPL: Create knowledge-graph-mcp/tools/manage.py
□ IMPL: Create knowledge-graph-mcp/Dockerfile
□ IMPL: Add CHROMA_* vars to .env.example
```

---

## Phase 4: Claude Code Agent Features → Agent Bot

### 4.1 Feature Comparison Matrix

| Feature | Claude Code Agent | Agent Bot Internal | Agent Bot External | Priority |
|---------|------------------|--------------------|--------------------|----------|
| **Agents** |
| Brain Orchestrator | ✅ | ✅ | - | - |
| Planning Agent | ✅ | ✅ | - | - |
| Executor Agent | ✅ | ✅ | - | - |
| Verifier Agent | ✅ | ✅ | - | - |
| Self-Improvement | ✅ | ❌ | - | HIGH |
| Agent Creator | ✅ | ❌ | - | MEDIUM |
| Skill Creator | ✅ | ❌ | - | MEDIUM |
| Webhook Generator | ✅ | ❌ | - | LOW |
| **Workflows** |
| GitHub Issue Handler | ✅ | Partial | - | HIGH |
| GitHub PR Review | ✅ | Partial | - | HIGH |
| Jira Code Plan | ✅ | Partial | - | HIGH |
| Slack Inquiry | ✅ | Partial | - | MEDIUM |
| **Dashboard** |
| Overview/Metrics | ✅ | ✅ | ✅ | - |
| Analytics/Costs | ✅ | Partial | ✅ | MEDIUM |
| Ledger | ✅ | ❌ | ✅ | LOW |
| Webhooks UI | ✅ | ✅ | ✅ | - |
| Chat/Conversations | ✅ | ✅ | ✅ | - |
| Registry (Agents) | ✅ | ❌ | ✅ | HIGH |
| Registry (Skills) | ✅ | ❌ | ✅ | HIGH |
| **Integrations** |
| OAuth Install UI | ✅ | ❌ | ❌ | HIGH |
| Flow Tracking | ✅ | Partial | Partial | MEDIUM |
| WebSocket Hub | ✅ | ✅ | ✅ | - |
| **Memory** |
| Learning System | ✅ | ❌ | - | HIGH |
| Pattern Storage | ✅ | ❌ | - | HIGH |
| Auto-Consolidation | ✅ | ❌ | - | MEDIUM |

### 4.2 High Priority Features to Port

#### 4.2.1 Self-Improvement Agent

**Location:** `agent-bot/agent-engine/.claude/agents/self-improvement.md`

**Triggers:**
- Verification score ≥ 90%
- Memory entries > 30 (consolidation)
- Same gap detected 2x in verification loop

**TDD Tasks:**
```
□ TEST: Self-improvement agent file exists and is valid
□ TEST: Brain delegates to self-improvement on verification success
□ TEST: Self-improvement writes to memory files
□ TEST: Memory consolidation triggers at threshold
□ IMPL: Create agents/self-improvement.md
□ IMPL: Add delegation logic to brain agent
□ IMPL: Create memory directory structure
□ IMPL: Implement consolidation triggers
```

#### 4.2.2 Workflow Agents

**GitHub Issue Handler:**
```
□ TEST: Issue webhook triggers github-issue-handler agent
□ TEST: Agent analyzes issue and posts response
□ TEST: Response includes analysis and next steps
□ IMPL: Create agents/workflows/github-issue-handler.md
□ IMPL: Add routing in brain agent
□ IMPL: Implement automatic response posting
```

**GitHub PR Review:**
```
□ TEST: PR webhook triggers github-pr-review agent
□ TEST: Agent reviews changes and posts comments
□ TEST: Review includes code suggestions
□ IMPL: Create agents/workflows/github-pr-review.md
□ IMPL: Add routing in brain agent
□ IMPL: Implement inline comment posting
```

**Jira Code Plan:**
```
□ TEST: Jira webhook triggers jira-code-plan agent
□ TEST: Agent creates plan and posts to ticket
□ TEST: Plan follows TDD structure
□ IMPL: Create agents/workflows/jira-code-plan.md
□ IMPL: Add routing in brain agent
□ IMPL: Implement Jira comment posting
```

#### 4.2.3 Registry Feature (Skills & Agents)

**API Endpoints:**
```
GET  /api/registry/agents          # List all agents
GET  /api/registry/agents/{name}   # Get agent details
GET  /api/registry/skills          # List all skills
GET  /api/registry/skills/{name}   # Get skill details
POST /api/registry/reload          # Reload from disk
```

**TDD Tasks:**
```
□ TEST: GET /api/registry/agents returns all agents
□ TEST: GET /api/registry/skills returns all skills
□ TEST: POST /api/registry/reload refreshes cache
□ TEST: Agent details include prompts and capabilities
□ IMPL: Create api/registry.py router
□ IMPL: Implement file system scanner for .claude/
□ IMPL: Add registry endpoints to dashboard-api
□ IMPL: Update external dashboard RegistryFeature
```

#### 4.2.4 Memory System

**Directory Structure:**
```
agent-bot/agent-engine/.claude/memory/
├── code/
│   └── patterns.md          # Code patterns learned
├── agents/
│   └── delegation.md        # Agent delegation learnings
├── process/
│   └── workflows.md         # Workflow learnings
├── project/
│   ├── decisions.md         # Project decisions
│   └── failures.md          # Common failure modes
└── stack/
    ├── python.md            # Python patterns
    ├── typescript.md        # TypeScript patterns
    └── go.md                # Go patterns
```

**TDD Tasks:**
```
□ TEST: Memory files are created on first learning
□ TEST: Patterns are appended, not overwritten
□ TEST: Consolidation merges similar patterns
□ TEST: Memory is accessible via brain agent context
□ IMPL: Create memory directory structure
□ IMPL: Create memory write skill
□ IMPL: Create memory read skill
□ IMPL: Implement consolidation logic
```

---

## Phase 5: OAuth Integration Button

### 5.1 UI Design

**Location:** External Dashboard → Settings or new "Integrations" page

**Components:**
```
┌─────────────────────────────────────────────────────────┐
│  INTEGRATIONS                                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │  🐙 GitHub      │  │  📋 Jira        │              │
│  │                 │  │                 │              │
│  │  Status: ✅     │  │  Status: ❌     │              │
│  │  Connected      │  │  Not Connected  │              │
│  │                 │  │                 │              │
│  │ [Disconnect]    │  │ [Connect]       │              │
│  └─────────────────┘  └─────────────────┘              │
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │  💬 Slack       │  │  🔍 Sentry      │              │
│  │                 │  │                 │              │
│  │  Status: ✅     │  │  Status: ❌     │              │
│  │  Connected      │  │  Not Connected  │              │
│  │                 │  │                 │              │
│  │ [Disconnect]    │  │ [Connect]       │              │
│  └─────────────────┘  └─────────────────┘              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 API Flow

```
1. User clicks "Connect GitHub"
2. Frontend calls: POST /api/oauth/install/github
3. Backend redirects to: https://github.com/login/oauth/authorize?...
4. User authorizes
5. GitHub redirects to: /oauth/callback/github?code=xxx
6. Backend exchanges code for token
7. Token stored encrypted in database
8. User redirected to: /integrations?success=github
```

### 5.3 API Endpoints

**Dashboard API additions:**
```
GET  /api/oauth/status              # Get all OAuth statuses
GET  /api/oauth/status/{platform}   # Get specific platform status
POST /api/oauth/install/{platform}  # Start OAuth flow (returns redirect URL)
DELETE /api/oauth/revoke/{platform} # Revoke OAuth connection
```

**OAuth Service (existing):**
```
GET  /oauth/install/{platform}      # Redirect to provider
GET  /oauth/callback/{platform}     # Handle callback
GET  /oauth/installations           # List installations
DELETE /oauth/installations/{id}    # Revoke
```

### 5.4 TDD Tasks for OAuth Integration

**Backend:**
```
□ TEST: GET /api/oauth/status returns all platform statuses
□ TEST: POST /api/oauth/install/github returns redirect URL
□ TEST: DELETE /api/oauth/revoke/github removes installation
□ TEST: Status shows "connected" after successful OAuth
□ TEST: Status shows "not_connected" when no installation
□ IMPL: Create api/oauth_status.py router
□ IMPL: Add proxy to oauth-service endpoints
□ IMPL: Add oauth endpoints to dashboard-api
```

**Frontend:**
```
□ TEST: IntegrationsFeature renders all platforms
□ TEST: Connect button opens OAuth flow
□ TEST: Status updates after successful connection
□ TEST: Disconnect button revokes and updates status
□ IMPL: Create features/integrations/IntegrationsFeature.tsx
□ IMPL: Create features/integrations/IntegrationCard.tsx
□ IMPL: Create features/integrations/hooks/useOAuthStatus.ts
□ IMPL: Add /integrations route to App.tsx
□ IMPL: Add Integrations to Sidebar navigation
```

### 5.5 Component Implementation

**IntegrationsFeature.tsx:**
```typescript
interface OAuthStatus {
  platform: string;
  connected: boolean;
  installedAt?: string;
  scopes?: string[];
}

function IntegrationsFeature() {
  const { statuses, isLoading } = useOAuthStatus();
  const connectMutation = useOAuthConnect();
  const disconnectMutation = useOAuthDisconnect();

  const handleConnect = (platform: string) => {
    // Opens OAuth flow in new window/redirect
    window.location.href = `/api/oauth/install/${platform}`;
  };

  const handleDisconnect = async (platform: string) => {
    await disconnectMutation.mutateAsync(platform);
  };

  return (
    <div className="space-y-8">
      <section className="panel" data-label="INTEGRATIONS">
        <h2>OAuth Connections</h2>
        <div className="grid grid-cols-2 gap-4">
          {PLATFORMS.map(platform => (
            <IntegrationCard
              key={platform}
              platform={platform}
              status={statuses?.[platform]}
              onConnect={() => handleConnect(platform)}
              onDisconnect={() => handleDisconnect(platform)}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
```

---

## Phase 6: Dashboard Feature Parity

### 6.1 Internal Dashboard (Agent Engine)

**Current State:** Basic HTML/CSS/JS in `agent-engine/dashboard/static/`

**Target:** Match external dashboard features

**Features to Add:**
1. ✅ Task monitoring (exists)
2. ❌ Analytics/costs visualization
3. ❌ Registry (agents/skills)
4. ❌ Integrations status
5. ❌ Memory viewer

**Decision:** The internal dashboard is simpler by design. Focus on:
- Adding Registry tab (read-only)
- Adding Integrations status (read-only)
- Keep analytics in external dashboard only

### 6.2 External Dashboard Feature Additions

**Current Routes:**
```
/              → OverviewFeature
/analytics     → AnalyticsFeature
/ledger        → LedgerFeature
/webhooks      → WebhooksFeature
/chat          → ChatFeature
/registry      → RegistryFeature
```

**New Routes:**
```
/integrations  → IntegrationsFeature (NEW)
/memory        → MemoryFeature (NEW - optional)
```

### 6.3 TDD Tasks for Dashboard Parity

**External Dashboard:**
```
□ TEST: /integrations route renders IntegrationsFeature
□ TEST: Sidebar shows Integrations link
□ TEST: RegistryFeature shows agents and skills
□ TEST: OverviewFeature shows integration status summary
□ IMPL: Create IntegrationsFeature component
□ IMPL: Update Sidebar with Integrations link
□ IMPL: Update RegistryFeature with skills tab
□ IMPL: Add integration status to Overview
```

**Internal Dashboard:**
```
□ TEST: Registry tab loads and shows agents
□ TEST: Integrations status displays correctly
□ IMPL: Add registry tab to internal dashboard
□ IMPL: Add integrations status panel
□ IMPL: Style consistency with external dashboard
```

---

## Phase 7: API Endpoint Alignment

### 7.1 Required API Additions

**Dashboard API (`dashboard-api/`):**

| Endpoint | Method | Description | Priority |
|----------|--------|-------------|----------|
| `/api/oauth/status` | GET | Get all OAuth statuses | HIGH |
| `/api/oauth/status/{platform}` | GET | Get platform status | HIGH |
| `/api/oauth/install/{platform}` | POST | Start OAuth flow | HIGH |
| `/api/oauth/revoke/{platform}` | DELETE | Revoke OAuth | HIGH |
| `/api/registry/agents` | GET | List agents | HIGH |
| `/api/registry/agents/{name}` | GET | Get agent details | HIGH |
| `/api/registry/skills` | GET | List skills | HIGH |
| `/api/registry/skills/{name}` | GET | Get skill details | HIGH |
| `/api/registry/reload` | POST | Reload registry | MEDIUM |
| `/api/memory` | GET | Get memory entries | LOW |
| `/api/memory/{category}` | GET | Get category entries | LOW |

### 7.2 TDD Tasks for API

```
□ TEST: All new endpoints return correct response schema
□ TEST: OAuth status endpoint reflects actual installations
□ TEST: Registry endpoints scan .claude/ directory correctly
□ TEST: Memory endpoints read markdown files correctly
□ TEST: Error handling for missing agents/skills
□ IMPL: Create api/oauth_status.py
□ IMPL: Create api/registry.py
□ IMPL: Create api/memory.py (optional)
□ IMPL: Add routers to main.py
□ IMPL: Update OpenAPI documentation
```

---

## Implementation Schedule

### Week 1: Foundation
- [ ] Environment variable consolidation
- [ ] Makefile refactoring with scripts
- [ ] ChromaDB Docker integration

### Week 2: Core Features
- [ ] Self-improvement agent
- [ ] Memory system implementation
- [ ] Workflow agents (GitHub, Jira)

### Week 3: Dashboard & OAuth
- [ ] OAuth integration button (backend)
- [ ] OAuth integration button (frontend)
- [ ] Registry feature (backend + frontend)

### Week 4: Polish & Testing
- [ ] Dashboard feature parity
- [ ] End-to-end testing
- [ ] Documentation updates

---

## Test Categories

### Unit Tests
- Individual tool functions
- API endpoint handlers
- React component rendering

### Integration Tests
- OAuth flow (mock provider)
- ChromaDB operations
- Agent delegation chain

### E2E Tests
- Full OAuth flow in browser
- Task creation → completion
- Dashboard real-time updates

---

## File Checklist

### New Files to Create

```
# Scripts
scripts/cli/start.sh
scripts/cli/stop.sh
scripts/cli/logs.sh
scripts/services/start.sh
scripts/services/stop.sh
scripts/services/health.sh
scripts/test/run-all.sh
scripts/test/run-service.sh
scripts/test/coverage.sh
scripts/db/migrate.sh
scripts/db/upgrade.sh
scripts/env/validate.sh
scripts/utils/clean.sh
scripts/utils/help.sh

# ChromaDB
mcp-servers/knowledge-graph-mcp/main.py
mcp-servers/knowledge-graph-mcp/server.py
mcp-servers/knowledge-graph-mcp/tools/store.py
mcp-servers/knowledge-graph-mcp/tools/query.py
mcp-servers/knowledge-graph-mcp/tools/manage.py
mcp-servers/knowledge-graph-mcp/models.py
mcp-servers/knowledge-graph-mcp/config.py
mcp-servers/knowledge-graph-mcp/Dockerfile
mcp-servers/knowledge-graph-mcp/requirements.txt
mcp-servers/knowledge-graph-mcp/tests/test_store.py
mcp-servers/knowledge-graph-mcp/tests/test_query.py

# Agents
agent-engine/.claude/agents/self-improvement.md
agent-engine/.claude/agents/workflows/github-issue-handler.md
agent-engine/.claude/agents/workflows/github-pr-review.md
agent-engine/.claude/agents/workflows/jira-code-plan.md
agent-engine/.claude/agents/workflows/slack-inquiry.md

# Memory
agent-engine/.claude/memory/code/patterns.md
agent-engine/.claude/memory/agents/delegation.md
agent-engine/.claude/memory/process/workflows.md
agent-engine/.claude/memory/project/decisions.md
agent-engine/.claude/memory/project/failures.md

# API
dashboard-api/api/oauth_status.py
dashboard-api/api/registry.py
dashboard-api/tests/test_oauth_status.py
dashboard-api/tests/test_registry.py

# Frontend
external-dashboard/src/features/integrations/IntegrationsFeature.tsx
external-dashboard/src/features/integrations/IntegrationCard.tsx
external-dashboard/src/features/integrations/hooks/useOAuthStatus.ts
external-dashboard/src/features/integrations/Integrations.test.tsx
```

### Files to Modify

```
# Root
.env.example (consolidate)
docker-compose.yml (add chromadb)
docker-compose.cli.yml (verify)
Makefile (simplify)

# Dashboard API
dashboard-api/main.py (add routers)

# External Dashboard
external-dashboard/src/App.tsx (add routes)
external-dashboard/src/components/ui/Sidebar.tsx (add links)
external-dashboard/src/features/registry/RegistryFeature.tsx (add skills)

# Agent Engine
agent-engine/.claude/agents/brain.md (add delegation)
```

### Files to Delete

```
# Service-specific .env.example (after consolidation)
agent-engine/.env.example
api-gateway/.env.example
dashboard-api/.env.example
oauth-service/.env.example
api-services/github-api/.env.example
api-services/jira-api/.env.example
api-services/slack-api/.env.example
api-services/sentry-api/.env.example
mcp-servers/jira-mcp/.env.example
mcp-servers/slack-mcp/.env.example
mcp-servers/sentry-mcp/.env.example
```

---

## Success Criteria

1. **Environment**: Single `.env.example` with all variables documented
2. **Makefile**: < 100 lines, all logic in scripts
3. **ChromaDB**: Container healthy, tools functional
4. **OAuth UI**: Can connect/disconnect all 4 platforms
5. **Registry**: Shows all agents and skills with details
6. **Memory**: Self-improvement writes learnings
7. **Tests**: 80%+ coverage on new code
8. **Dashboards**: Feature parity where applicable
