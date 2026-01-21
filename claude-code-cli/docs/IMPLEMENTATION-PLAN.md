# Machine Management System - Implementation Plan

## Project Location

> [!IMPORTANT]
> **Project Directory**: `claude-code-agent/`
> 
> This is a NEW project created in an external directory, not inside `claude-code-cli`.

---

## Goal

Build a **unified container** where:
- **FastAPI** runs as daemon (always on) - handles webhooks and dashboard
- **Claude Code CLI** spawns on-demand per request - does actual work
- **Sub-agents** = Claude CLI instances running from different working directories

---

## Core Technical Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Pydantic Everywhere** | ALL domain logic enforced via Pydantic models with validators |
| **uv Only** | Use `uv` exclusively (no pip) - `uv sync`, `uv add`, `uv run` |
| **Type Safety** | mypy strict mode, full typing |
| **Asyncio Native** | All I/O is async |
| **TDD** | Business logic tests first |
| **On-Demand CLI** | Claude CLI spawned per request, not always running |

> [!TIP]
> See [TECHNICAL-SPECIFICATION.md](./TECHNICAL-SPECIFICATION.md) for complete Pydantic models, patterns, and API specs.

> [!NOTE]
> See [BUSINESS-LOGIC.md](./BUSINESS-LOGIC.md) for complete flow definitions and business logic test cases.

---

## Development Workflow

> [!CAUTION]
> **MANDATORY WORKFLOW FOR EACH TASK:**
> 
> 1. **Write tests first** (RED state - tests fail)
> 2. **Implement code** until tests pass (GREEN state)
> 3. **Verify ALL tests pass**: `uv run pytest tests/ -v`
> 4. **Commit and Push**:
>    ```bash
>    git add .
>    git commit -m "feat: <task description>"
>    git push
>    ```
> 5. **Update PROGRESS.md** - mark task as completed
> 
> ⚠️ **Do NOT proceed to next task until steps 1-5 are complete!**

---

## Progress Tracking

Track progress in `PROGRESS.md`:

```markdown
# Implementation Progress

## Completed Tasks
- [x] Task 1: Description (commit: abc123)
- [x] Task 2: Description (commit: def456)

## In Progress
- [ ] Task 3: Description

## Pending
- [ ] Task 4: Description
```

---

## Architecture Decision

> [!IMPORTANT]
> **Execution Model: FastAPI Daemon + Claude CLI On-Demand**
> 
> - FastAPI server runs **forever** (daemon) - handles HTTP, WebSocket
> - Claude CLI is **spawned per task** - starts, works, exits
> - Sub-agents = Claude CLI with different `cwd` (working directory)

> [!WARNING]
> **Breaking Change**: Replacing 2 Docker containers (planning-agent + executor-agent) with 1 unified container.

---

## Proposed Changes

### Component 1: Directory Structure

```
agents/
├── unified/                          # NEW: Single unified agent
│   ├── Dockerfile
│   ├── main.py                       # Entry point
│   ├── brain.py                      # Brain orchestrator
│   ├── task_router.py                # Task → Agent routing
│   ├── background_manager.py         # Asyncio task pool
│   ├── subagent_registry.py          # Dynamic agent registry
│   ├── subagent_runner.py            # Run individual sub-agent
│   ├── entity_creator.py             # Create webhooks/agents/skills
│   ├── auth_manager.py               # Authentication management
│   ├── config_loader.py              # Load persisted configs
│   │
│   └── skills/                       # Built-in skills
│       ├── planning/SKILL.md
│       ├── execution/SKILL.md
│       ├── code_implementation/SKILL.md
│       ├── question_asking/SKILL.md
│       └── consultation/SKILL.md
│
├── planning-agent/                   # DEPRECATED (keep temporarily)
└── executor-agent/                   # DEPRECATED (keep temporarily)
```

---

### Component 2: Brain & Sub-Agent System

#### [NEW] `agents/unified/brain.py`

The Brain - main orchestrator that talks to Claude Code CLI:

```python
class MachineBrain:
    """Claude Code CLI as the Machine Brain."""
    
    def __init__(self, config_dir: Path):
        self.router = TaskRouter()
        self.manager = BackgroundTaskManager()
        self.registry = SubAgentRegistry()
        self.entity_creator = EntityCreator(self)
        
    async def process_message(self, message: str, session: Session) -> BrainResponse:
        """Process user message from dashboard chat."""
        # Invokes Claude Code CLI to understand intent
        # Routes to appropriate action (task/entity creation/question)
        
    async def route_webhook(self, source: str, payload: dict) -> Task:
        """Route incoming webhook to appropriate sub-agent."""
        
    async def create_entity(self, entity_type: str, spec: dict) -> Entity:
        """Create webhook/agent/skill via Claude Code CLI."""
```

#### [NEW] `agents/unified/background_manager.py`

```python
class BackgroundTaskManager:
    """Manages sub-agents as asyncio background tasks."""
    
    async def submit(self, task: Task, agent: SubAgent) -> str:
        """Submit task to run in background."""
        
    async def stream_output(self, task_id: str) -> AsyncIterator[str]:
        """Yield output chunks as they're produced."""
        
    async def send_input(self, task_id: str, message: str) -> None:
        """Send user message to running sub-agent."""
        
    async def stop(self, task_id: str) -> bool:
        """Stop a running sub-agent."""
```

---

### Component 3: Dashboard Conversational UI

#### [NEW] `services/dashboard/api/websocket.py`

```python
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time updates."""
    await websocket.accept()
    
    # Events from server:
    # - task.created, task.output, task.metrics, task.completed
    # - agent.status
    
    # Commands from client:
    # - task.input, task.stop
    # - chat.message
```

#### [NEW] Static Frontend

| Page | Features |
|------|----------|
| **Main Dashboard** | Machine status, active tasks, chat, cost graphs |
| **Task View** | Live output streaming, interaction panel |
| **Create Webhook** | Form / File upload / Chat with Brain |
| **Create Agent** | Form / Folder upload / Chat with Brain |
| **Settings** | Env vars, credentials upload |

---

### Component 4: Dynamic Entity Creation

#### [NEW] `agents/unified/entity_creator.py`

```python
class EntityCreator:
    """Creates webhooks, agents, skills via Brain."""
    
    async def create_webhook(self, 
        description: str = None,
        file_content: str = None,
        form_data: dict = None) -> Webhook:
        """Create webhook from any input method."""
        
    async def create_agent(self,
        description: str = None,
        folder_path: Path = None,
        form_data: dict = None) -> SubAgent:
        """Create sub-agent from any input method."""
        
    async def create_skill(self,
        target: str,  # "brain" or agent name
        skill_content: str) -> Skill:
        """Add skill to Brain or sub-agent."""
```

---

### Component 5: Persistence

#### Volume Mount Structure

```yaml
volumes:
  machine_data:
    driver: local
    
services:
  unified-agent:
    volumes:
      - machine_data:/data
```

#### Persisted Data

```
/data/
├── db/machine.db           # SQLite: tasks, sessions, metrics
├── config/
│   ├── webhooks/           # Dynamic webhooks
│   ├── agents/             # Dynamic sub-agents
│   ├── skills/             # Dynamic skills
│   └── env/                # Environment variables
└── credentials/            # Claude auth (optional)
```

---

### Component 6: Authentication

#### [NEW] `scripts/export-keychain-credentials.sh`

```bash
#!/bin/bash
# Export Claude credentials from macOS Keychain to JSON

CREDS_FILE="$HOME/.claude/credentials.json"
if [ -f "$CREDS_FILE" ]; then
    cat "$CREDS_FILE"
else
    echo "Error: Credentials not found at $CREDS_FILE" >&2
    exit 1
fi
```

#### [NEW] `agents/unified/auth_manager.py`

```python
class AuthManager:
    """Manages Claude authentication."""
    
    async def check_auth(self) -> AuthStatus:
        """Check if Claude is authenticated."""
        
    async def upload_credentials(self, creds_json: dict) -> bool:
        """Upload credentials from dashboard."""
        
    async def validate(self) -> bool:
        """Run 'claude --version' to verify auth."""
```

---

### Component 7: Task Model Updates

#### [MODIFY] `shared/models.py`

```diff
class BaseTask(BaseModel):
    ...
+   # Sub-agent tracking
+   assigned_agent: Optional[str] = None
+   session_id: Optional[str] = None
+   user_id: Optional[str] = None
+   
+   # Real-time streaming
+   output_stream: str = ""
+   is_interactive: bool = False
+   parent_task_id: Optional[str] = None

+class Session(BaseModel):
+    """Dashboard session."""
+    session_id: str
+    user_id: str
+    machine_id: str
+    connected_at: datetime
+    total_cost_usd: float = 0.0
+    active_tasks: List[str] = []
```

---

### Component 8: Docker Changes

#### [MODIFY] `infrastructure/docker/docker-compose.yml`

```diff
-  planning-agent:
-    build: ../../agents/planning-agent
-    ...
-    
-  executor-agent:
-    build: ../../agents/executor-agent
-    ...

+  unified-agent:
+    build: ../../agents/unified
+    volumes:
+      - machine_data:/data
+      - repos:/app/repos
+    ports:
+      - "8080:8080"  # Dashboard
+    environment:
+      - REDIS_URL=redis://redis:6379
+      - MACHINE_ID=${MACHINE_ID:-machine-001}
+      - MAX_CONCURRENT_TASKS=5
+    depends_on:
+      - redis

+volumes:
+  machine_data:
```

---

## Verification Plan

### Automated Tests (TDD - Business Logic Only)

```bash
# Run business logic tests (use uv only!)
cd /path/to/claude-code-cli

# 1. Brain routing tests
uv run pytest tests/unit/test_brain_routing.py -v

# 2. Sub-agent lifecycle tests
uv run pytest tests/unit/test_subagent_lifecycle.py -v

# 3. Dynamic creation tests
uv run pytest tests/unit/test_dynamic_creation.py -v

# 4. Persistence tests
uv run pytest tests/unit/test_persistence.py -v

# 5. Authentication tests
uv run pytest tests/unit/test_authentication.py -v

# 6. Session tracking tests
uv run pytest tests/unit/test_session_tracking.py -v

# 7. Real-time streaming tests
uv run pytest tests/unit/test_realtime.py -v

# Run all
uv run pytest tests/unit/ -v --tb=short
```

### Manual Verification

1. **Start system:**
   ```bash
   make rebuild
   docker-compose logs -f unified-agent
   ```

2. **Open dashboard:**
   - Navigate to http://localhost:8080
   - Verify chat works with Brain
   
3. **Create webhook via chat:**
   - "Create a webhook for GitLab merge requests"
   - Verify it appears in webhook list
   
4. **Trigger task:**
   - Send webhook or chat request
   - Verify task appears in Active Tasks
   - Click task → verify live streaming
   
5. **Test auth flow:**
   - Stop container, delete credentials
   - Restart → verify auth banner appears
   - Upload credentials → verify operations resume

---

## File Summary

| Action | Path | Description |
|--------|------|-------------|
| NEW | `agents/unified/` | Unified agent with Brain |
| NEW | `agents/unified/brain.py` | Main Brain orchestrator |
| NEW | `agents/unified/background_manager.py` | Asyncio task management |
| NEW | `agents/unified/entity_creator.py` | Dynamic entity creation |
| NEW | `agents/unified/auth_manager.py` | Authentication management |
| NEW | `services/dashboard/api/websocket.py` | WebSocket real-time |
| NEW | `services/dashboard/static/` | Dashboard frontend |
| NEW | `scripts/export-keychain-credentials.sh` | Keychain export |
| MODIFY | `shared/models.py` | Add session/agent tracking |
| MODIFY | `docker-compose.yml` | Single unified container |
| NEW | `tests/unit/test_*.py` | Business logic TDD tests |
| DEPRECATED | `agents/planning-agent/` | Keep temporarily |
| DEPRECATED | `agents/executor-agent/` | Keep temporarily |

---

*Created: 2026-01-21*
