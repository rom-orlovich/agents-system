# Business Logic & System Flow

> **Project Directory**: `claude-code-agent/`

> [!CAUTION]
> **WORKFLOW**: Tests pass → `git commit && push` → Update `PROGRESS.md`

---

## 🎯 Vision

**"FastAPI Daemon + Claude Code CLI On-Demand"**

A single Docker container with two components:
1. **FastAPI Server (DAEMON)** - Always running, handles webhooks and dashboard
2. **Claude Code CLI (ON-DEMAND)** - Spawned per request, does the actual work, then exits

> [!IMPORTANT]
> **Key Insight**: Claude CLI is NOT a server. It's a command-line tool.
> - It starts, does work, exits
> - We spawn a new instance for each task
> - Sub-agents = Claude CLI running from different directories

---

## 📋 Core Business Logic

### 1. Execution Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXECUTION MODEL                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   WHAT RUNS FOREVER (DAEMON):                                                │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  FastAPI Server (uvicorn main:app --host 0.0.0.0 --port 8000)       │   │
│   │  • Listens for webhooks                                              │   │
│   │  • Serves dashboard API                                              │   │
│   │  • Manages WebSocket connections                                     │   │
│   │  • Runs task queue worker                                            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   WHAT RUNS PER REQUEST (ON-DEMAND):                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Claude Code CLI (spawned as subprocess)                             │   │
│   │  • Starts when task is assigned                                      │   │
│   │  • Reads CLAUDE.md from its working directory                        │   │
│   │  • Does the work                                                      │   │
│   │  • Streams output to stdout                                           │   │
│   │  • Exits when done                                                    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Request Flow (Sequence)

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ User/   │     │ FastAPI │     │  Redis  │     │ Worker  │     │ Claude  │
│ Webhook │     │ Server  │     │  Queue  │     │ (async) │     │   CLI   │
└────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘
     │               │               │               │               │
     │  POST /chat   │               │               │               │
     ├──────────────►│               │               │               │
     │               │ push(task)    │               │               │
     │               ├──────────────►│               │               │
     │               │               │ pop(task)     │               │
     │               │               │◄──────────────│               │
     │               │               │               │               │
     │               │               │               │ spawn(claude) │
     │               │               │               ├──────────────►│
     │               │               │               │               │
     │               │               │               │◄──stream──────│
     │◄─────────WebSocket────────────┼───────────────│               │
     │               │               │               │               │
     │               │               │               │◄──result──────│
     │               │               │               │    (exit)     │
     │               │               │               │               │
```

---

### 3. Sub-Agents = Different Working Directories

```bash
# Brain (main)
claude -p "Decide what to do" --cwd /app/
# Reads: /app/.claude/CLAUDE.md

# Planning Agent
claude -p "Create a plan" --cwd /app/agents/planning/
# Reads: /app/agents/planning/.claude/CLAUDE.md

# Executor Agent
claude -p "Implement the fix" --cwd /app/agents/executor/
# Reads: /app/agents/executor/.claude/CLAUDE.md

# Custom Agent
claude -p "Review security" --cwd /app/agents/security-reviewer/
# Reads: /app/agents/security-reviewer/.claude/CLAUDE.md
```

---

### 4. Dashboard UI - Conversational Interface

**Core Features:**

| Feature | Description |
|---------|-------------|
| **Chat with Machine** | Send messages → spawns Claude CLI → returns response |
| **Live Sub-Agent View** | See all running CLI processes in real-time |
| **Task Interaction** | Click on a task → view live stdout stream |
| **Stop/Control Agents** | Stop = kill the subprocess (SIGTERM) |
| **Create Webhooks** | Upload file or fill form → save to /data/config/ |
| **Create Sub-Agents** | Upload folder → save to /app/agents/{name}/ |
| **Create Skills** | Upload SKILL.md → save to agent's skills/ |
| **Set Environment** | Upload .env → save to /data/config/env/ |
| **Credential Upload** | Upload JSON → validate → save to /data/credentials/ |
| **Cost Graphs** | Per-user, per-session cost tracking with charts |
| **Task History** | All tasks with filtering by agent, status, user |

---

### 3. Task Flow (Business Logic)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           TASK LIFECYCLE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐                                                        │
│  │   SOURCE    │  Dashboard Chat / Webhook / Direct API                 │
│  └──────┬──────┘                                                        │
│         │                                                                │
│         ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BRAIN (Claude Code CLI)                       │   │
│  │                                                                   │   │
│  │  1. Parse incoming request                                        │   │
│  │  2. Determine task type                                           │   │
│  │  3. Select/Create appropriate sub-agent                           │   │
│  │  4. Spawn sub-agent as background task                            │   │
│  │  5. Return task_id for tracking                                   │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                        │
│                                 ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SUB-AGENT EXECUTION                           │   │
│  │                                                                   │   │
│  │  Status: QUEUED → RUNNING → COMPLETED/FAILED                     │   │
│  │                                                                   │   │
│  │  • Streams output to Dashboard (WebSocket)                        │   │
│  │  • Accepts input from Dashboard (user interaction)                │   │
│  │  • Updates metrics (cost, tokens, duration)                       │   │
│  │  • Persists results to database                                   │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                        │
│                                 ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DASHBOARD DISPLAY                             │   │
│  │                                                                   │   │
│  │  • Live task output streaming                                     │   │
│  │  • Cost updates in real-time                                      │   │
│  │  • Agent status indicators                                        │   │
│  │  • Interaction panel for active tasks                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 4. Dynamic Entity Creation Flow

#### 4.1 Create Webhook

```
User Action                    System Response
─────────────────────────────────────────────────────────
1. Dashboard: "Add Webhook"    → Show 3 options:
                                  a) Describe in chat
                                  b) Upload webhook file
                                  c) Fill form

2a. Chat: "I want a webhook    → Brain analyzes request
    for GitLab merge events"   → Creates webhook handler code
                               → Saves to /config/webhooks/
                               → Hot-reloads webhook server
                               → Returns: "Webhook created at /webhooks/gitlab"

2b. Upload: gitlab_webhook.py  → Validates file structure
                               → Saves to /config/webhooks/
                               → Hot-reloads webhook server

2c. Form: name, url pattern,   → Generates webhook handler
    event types, target agent  → Saves and hot-reloads
```

#### 4.2 Create Sub-Agent

```
User Action                    System Response
─────────────────────────────────────────────────────────
1. Dashboard: "Add Agent"      → Show 3 options:
                                  a) Describe in chat
                                  b) Upload agent folder
                                  c) Fill form

2a. Chat: "Create an agent     → Brain creates:
    for code review that          - /config/agents/code-reviewer/
    focuses on security"          - SKILL.md
                                  - config.yaml
                               → Registers agent
                               → Returns: "Agent 'code-reviewer' ready"

2b. Upload: code-reviewer/     → Validates folder structure
    ├── SKILL.md               → Saves to /config/agents/
    ├── config.yaml            → Registers agent
    └── scripts/

2c. Form: name, description,   → Generates agent files
    skills, priority           → Saves and registers
```

#### 4.3 Create Skills

```
User Action                    System Response
─────────────────────────────────────────────────────────
1. Dashboard: "Add Skill"      → Select target: Brain / Sub-agent
                               → Show options: Chat / Upload / Form

2. Skill creation             → Validates SKILL.md format
                              → Saves to appropriate directory
                              → Updates agent's skill list
```

---

### 5. Persistence Model

**All dynamic entities persist across restarts:**

```
/data/                          # Persistent volume mount
  ├── db/
  │   └── machine.db            # SQLite: tasks, sessions, metrics
  │
  ├── config/
  │   ├── webhooks/             # Dynamic webhook handlers
  │   │   ├── registry.yaml     # Webhook registry
  │   │   └── handlers/         # Webhook handler files
  │   │
  │   ├── agents/               # Dynamic sub-agents
  │   │   ├── registry.yaml     # Agent registry
  │   │   └── {agent-name}/     # Agent folders
  │   │       ├── SKILL.md
  │   │       ├── config.yaml
  │   │       └── scripts/
  │   │
  │   ├── skills/               # Brain skills
  │   │   └── {skill-name}/
  │   │       └── SKILL.md
  │   │
  │   └── env/                  # Environment configs
  │       └── .env              # Persisted env vars
  │
  └── credentials/
      └── claude-auth.json      # Claude credentials (optional)
```

---

### 6. Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AUTHENTICATION FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Startup                                                                 │
│  ───────                                                                 │
│  1. Check ~/.claude/credentials.json                                     │
│  2. If valid → Ready                                                     │
│  3. If expired → Try refresh token                                       │
│  4. If failed/missing → Mark as NEEDS_AUTH                              │
│                                                                          │
│  Dashboard Display (when NEEDS_AUTH)                                     │
│  ─────────────────────────────────────                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ⚠️ Claude Authentication Required                               │   │
│  │                                                                   │   │
│  │  Option 1: Run on your local machine:                            │   │
│  │  ┌─────────────────────────────────────────────────────────┐    │   │
│  │  │ ./scripts/export-keychain-credentials.sh > creds.json   │    │   │
│  │  └─────────────────────────────────────────────────────────┘    │   │
│  │                                                                   │   │
│  │  Option 2: Upload existing credentials:                          │   │
│  │  [  📁 Upload credentials.json  ]                                │   │
│  │                                                                   │   │
│  │  Option 3: Manual OAuth:                                          │   │
│  │  [  🔐 Start OAuth Flow  ]                                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  After Upload                                                            │
│  ────────────                                                            │
│  1. Validate credential structure                                        │
│  2. Test with: claude --version                                         │
│  3. If valid → Save to /data/credentials/ → Ready                      │
│  4. If invalid → Show error, retry                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 7. Session & User Tracking

**Each dashboard connection is a session:**

```python
Session:
  session_id: str          # Unique session identifier
  user_id: str             # From Claude auth (account ID)
  machine_id: str          # Container/machine identifier
  connected_at: datetime
  
  # Per-session metrics
  total_cost_usd: float
  total_tasks: int
  active_tasks: List[str]  # task_ids

Task:
  task_id: str
  session_id: str          # Which session created this
  user_id: str             # Which user owns this
  agent_name: str          # Which sub-agent is handling
  
  # Live metrics (WebSocket updates)
  status: TaskStatus
  cost_usd: float
  input_tokens: int
  output_tokens: int
  duration_seconds: float
  output_stream: str       # Live output
```

---

### 8. Real-Time Updates (WebSocket)

```
Dashboard ←──WebSocket──→ Server

Events:
  ← task.created(task_id, agent, status)
  ← task.output(task_id, chunk)           # Live streaming
  ← task.metrics(task_id, cost, tokens)   # Real-time cost
  ← task.completed(task_id, result)
  ← task.failed(task_id, error)
  ← agent.status(agent_name, status)
  
  → task.input(task_id, message)          # User interaction
  → task.stop(task_id)                    # Stop task
  → chat.message(message)                 # Chat with brain
```

---

## 🧪 TDD - Business Logic Tests

### Test Categories (NO Implementation Details)

```python
# =============================================================================
# 1. BRAIN ROUTING TESTS - Does the brain route correctly?
# =============================================================================

def test_brain_routes_jira_task_to_planning_agent():
    """When Jira webhook → Brain routes to planning agent."""
    
def test_brain_routes_approved_task_to_executor_agent():
    """When task approved → Brain routes to executor agent."""
    
def test_brain_routes_question_to_question_agent():
    """When user asks question → Brain routes to question agent."""

def test_brain_routes_to_custom_agent_if_registered():
    """When custom agent matches task → Brain routes to custom agent."""


# =============================================================================
# 2. SUB-AGENT LIFECYCLE TESTS - Do sub-agents work correctly?
# =============================================================================

def test_subagent_starts_in_background():
    """When task submitted → Sub-agent runs in background."""

def test_subagent_streams_output():
    """While running → Sub-agent streams output to dashboard."""

def test_subagent_accepts_user_input():
    """While running → Sub-agent can receive user messages."""

def test_subagent_can_be_stopped():
    """While running → Sub-agent can be stopped by user."""

def test_subagent_reports_metrics():
    """While running → Sub-agent reports cost/tokens/duration."""

def test_subagent_persists_result():
    """When completed → Result is persisted to database."""


# =============================================================================
# 3. DYNAMIC CREATION TESTS - Can entities be created dynamically?
# =============================================================================

def test_webhook_created_from_description():
    """When user describes webhook → Brain creates webhook handler."""

def test_webhook_created_from_file_upload():
    """When user uploads webhook file → System registers webhook."""

def test_webhook_activates_immediately():
    """When webhook created → It handles requests immediately."""

def test_agent_created_from_description():
    """When user describes agent → Brain creates agent files."""

def test_agent_created_from_folder_upload():
    """When user uploads agent folder → System registers agent."""

def test_skill_added_to_brain():
    """When skill uploaded for brain → Brain can use skill."""

def test_skill_added_to_subagent():
    """When skill uploaded for sub-agent → Sub-agent can use skill."""


# =============================================================================
# 4. PERSISTENCE TESTS - Does data survive restarts?
# =============================================================================

def test_webhooks_persist_across_restart():
    """When container restarts → Previously created webhooks work."""

def test_agents_persist_across_restart():
    """When container restarts → Previously created agents available."""

def test_skills_persist_across_restart():
    """When container restarts → Previously created skills available."""

def test_env_vars_persist_across_restart():
    """When container restarts → Previously set env vars active."""

def test_tasks_persist_across_restart():
    """When container restarts → Task history available."""


# =============================================================================
# 5. AUTHENTICATION TESTS - Does auth flow work?
# =============================================================================

def test_valid_credentials_allow_operation():
    """When valid credentials → Claude Code CLI works."""

def test_expired_credentials_trigger_auth_needed():
    """When credentials expired → System shows auth needed."""

def test_credential_upload_enables_operation():
    """When user uploads valid credentials → System becomes operational."""

def test_invalid_credential_upload_shows_error():
    """When user uploads invalid credentials → Error message shown."""

def test_keychain_export_script_produces_valid_json():
    """When running export script → Valid JSON credentials produced."""


# =============================================================================
# 6. SESSION & METRICS TESTS - Is tracking correct?
# =============================================================================

def test_session_tracks_user_id():
    """When user connects → Session linked to user ID."""

def test_session_tracks_costs_separately():
    """When multiple users → Each session has separate cost tracking."""

def test_task_linked_to_session():
    """When task created → Task linked to creating session."""

def test_dashboard_shows_user_tasks_only():
    """When viewing dashboard → Only user's own tasks shown (or all if admin)."""

def test_cost_graph_shows_per_agent_breakdown():
    """When viewing costs → Breakdown by agent visible."""


# =============================================================================
# 7. REAL-TIME TESTS - Do updates stream correctly?
# =============================================================================

def test_task_output_streams_to_dashboard():
    """When sub-agent produces output → Dashboard receives via WebSocket."""

def test_metrics_update_in_realtime():
    """When cost changes → Dashboard updates immediately."""

def test_user_message_reaches_subagent():
    """When user sends message to task → Sub-agent receives it."""

def test_stop_command_stops_subagent():
    """When user clicks stop → Sub-agent stops."""
```

---

## 🔄 Complete System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              COMPLETE FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STARTUP                                                                     │
│  ───────                                                                     │
│  1. Container starts                                                         │
│  2. Load persisted config (webhooks, agents, skills, env)                   │
│  3. Check Claude authentication                                              │
│  4. Start webhook server                                                     │
│  5. Start dashboard server                                                   │
│  6. Brain ready to receive commands                                          │
│                                                                              │
│  USER CONNECTS TO DASHBOARD                                                  │
│  ─────────────────────────                                                   │
│  1. WebSocket connection established                                         │
│  2. Session created with user_id (from auth)                                 │
│  3. Load user's task history and metrics                                     │
│  4. Display dashboard: chat, agents, tasks, costs                            │
│                                                                              │
│  USER CHATS WITH BRAIN                                                       │
│  ────────────────────                                                        │
│  1. User: "Fix the authentication bug in the API"                            │
│  2. Brain: Creates task, selects planning agent                              │
│  3. Task appears in dashboard as "Running"                                   │
│  4. Sub-agent output streams to dashboard                                    │
│  5. User can click task → enter conversation with sub-agent                  │
│  6. Sub-agent completes → result shown, metrics updated                      │
│                                                                              │
│  WEBHOOK TRIGGERS TASK                                                       │
│  ────────────────────                                                        │
│  1. External event (Jira, GitHub, Sentry, Slack, Custom)                    │
│  2. Webhook server receives request                                          │
│  3. Creates task in queue                                                    │
│  4. Brain routes to appropriate sub-agent                                    │
│  5. Task visible in dashboard (if user connected)                            │
│  6. User can interact with the running sub-agent                             │
│                                                                              │
│  USER CREATES WEBHOOK                                                        │
│  ───────────────────                                                         │
│  1. Dashboard: "I need a webhook for Bitbucket PRs"                          │
│  2. Brain: Creates /config/webhooks/handlers/bitbucket.py                   │
│  3. Brain: Updates /config/webhooks/registry.yaml                           │
│  4. Webhook server hot-reloads                                               │
│  5. Brain: "Webhook ready at /webhooks/bitbucket"                            │
│                                                                              │
│  AUTH EXPIRES                                                                │
│  ───────────                                                                 │
│  1. Claude CLI returns auth error                                            │
│  2. Dashboard shows auth needed banner                                       │
│  3. User runs local script: ./export-keychain-credentials.sh                │
│  4. User uploads produced JSON file                                          │
│  5. System validates → tests → activates                                     │
│  6. Operations resume                                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Dashboard UI Mockup

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 Claude Machine Dashboard                     user@example.com    [⚙️]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ MACHINE STATUS ─────────────────────────────────────────────────────┐  │
│  │  Machine ID: claude-prod-001          Status: 🟢 Operational         │  │
│  │  Active Agents: 3/5                   Session Cost: $2.47            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ ACTIVE TASKS ───────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  ▶ task-001 | Planning Agent | "Analyzing Sentry error..." | $0.32  │  │
│  │    └─ [View] [Stop] [Chat]                                           │  │
│  │                                                                       │  │
│  │  ▶ task-002 | Executor Agent | "Running tests..."        | $0.18   │  │
│  │    └─ [View] [Stop] [Chat]                                           │  │
│  │                                                                       │  │
│  │  ▶ task-003 | Custom: sec-review | "Reviewing auth..."   | $0.51   │  │
│  │    └─ [View] [Stop] [Chat]                                           │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ CHAT WITH MACHINE ─────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  You: Fix the authentication bug in API endpoint /login              │  │
│  │                                                                       │  │
│  │  🤖: I'll create a planning task for this. Starting analysis...     │  │
│  │      Task ID: task-004 | Agent: Planning                             │  │
│  │      [View Task Progress]                                             │  │
│  │                                                                       │  │
│  │  ────────────────────────────────────────────────────────────────   │  │
│  │  [Type a message...]                                      [Send]    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ COST BREAKDOWN ─────────────────────────────────────────────────────┐  │
│  │  📊 Today: $12.47  |  This Week: $84.32  |  This Month: $342.18     │  │
│  │                                                                       │  │
│  │  By Agent:                                                            │  │
│  │  ████████████░░░░░░  Planning: $5.23 (42%)                           │  │
│  │  ██████░░░░░░░░░░░░  Executor: $3.12 (25%)                           │  │
│  │  ████░░░░░░░░░░░░░░  Custom:   $2.67 (21%)                           │  │
│  │  ███░░░░░░░░░░░░░░░  Other:    $1.45 (12%)                           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ QUICK ACTIONS ──────────────────────────────────────────────────────┐  │
│  │  [+ Add Webhook]  [+ Add Agent]  [+ Add Skill]  [⚙️ Set Env]  [🔐 Auth] │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*Created: 2026-01-21*
