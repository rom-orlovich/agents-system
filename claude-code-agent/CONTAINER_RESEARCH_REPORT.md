# Container Filesystem Research Report

**Date:** 2026-01-22
**Machine ID:** claude-code-agent
**Container Location:** `/app`

---

## Executive Summary

This Claude Code Agent container is a **self-managing orchestration system** running FastAPI as a daemon with on-demand Claude CLI spawning. The architecture supports:

- **3 Built-in Subagents** (Planning, Executor, Orchestration)
- **1 Active Skill** (webhook-management)
- **Dynamic Agent/Skill Upload** via dashboard/API
- **Persistent Storage** in `/data` volume
- **Unified Webhook System** for GitHub/Jira/Slack integration

---

## 1. Container Architecture

### Directory Structure

```
/app/                               # Main application root
├── .claude/                        # Claude Code native config
│   ├── CLAUDE.md                   # Brain agent instructions
│   ├── agents/                     # Built-in subagents (3)
│   │   ├── planning.md             # Analysis & bug investigation
│   │   ├── executor.md             # Code implementation
│   │   └── orchestration.md        # System operations
│   └── skills/                     # Native skills (1)
│       └── webhook-management/     # Webhook lifecycle management
│           └── SKILL.md
│
├── api/                            # FastAPI routes
│   ├── webhooks.py                 # Webhook endpoints
│   ├── conversations.py            # Chat history API
│   ├── dashboard.py                # Dashboard API
│   ├── registry.py                 # Skill/Agent upload API
│   └── ... (12 total modules)
│
├── core/                           # Business logic
│   ├── cli_runner.py               # Claude CLI executor
│   ├── webhook_engine.py           # Webhook processor
│   ├── websocket_hub.py            # Real-time broadcast
│   ├── database/                   # SQLite + Redis
│   └── ... (12 total modules)
│
├── shared/                         # Domain models
│   └── machine_models.py           # Pydantic models (ALL business rules)
│
├── workers/                        # Background tasks
│   └── task_worker.py              # Queue processor (spawns Claude CLI)
│
├── services/                       # Frontend
│   └── dashboard/                  # WebSocket-based UI
│
├── docs/                           # Documentation (13 files)
├── tests/                          # Test suite
├── data/                           # Persistent volume (runtime)
└── ... (config, scripts, etc.)
```

---

## 2. Subagents (Built-in)

### 2.1 Planning Agent
**File:** `.claude/agents/planning.md`
**Model:** sonnet
**Tools:** Read, Grep, FindByName, ListDir, RunCommand

**Purpose:** Analyze bugs/issues and create fix plans (NO implementation)

**Capabilities:**
- Read code via MCP GitHub
- Query Sentry for errors
- Search codebases for architecture understanding
- Create `PLAN.md` files with detailed strategies
- Open draft PRs with plans
- Comment on Jira tickets

**Output Format:**
```markdown
# Fix Plan: [Issue Title]
## Issue Summary
## Root Cause
## Affected Components
## Fix Strategy (step-by-step)
## Files to Modify
## Testing Strategy
## Risks & Considerations
## Complexity: [Simple|Medium|Complex]
```

**Skills Referenced:**
- discovery
- jira-enrichment
- plan-creation

---

### 2.2 Executor Agent
**File:** `.claude/agents/executor.md`
**Model:** sonnet
**Tools:** Read, Write, Edit, MultiEdit, Grep, FindByName, ListDir, RunCommand
**Permission Mode:** acceptEdits

**Purpose:** Implement code changes based on plans

**Capabilities:**
- Write/edit code files
- Run tests (unit, integration, e2e)
- Create git commits with clear messages
- Open pull requests
- Fix linting/type errors
- Refactor code
- Add documentation

**Process:**
1. **Understand Plan** → Read PLAN.md thoroughly
2. **TDD Implementation** → Write tests first, implement, refactor
3. **Verify & Document** → Run tests, check regressions, create PR

**Quality Checklist:**
- [ ] All tests pass
- [ ] No linting/type errors
- [ ] Code documented
- [ ] Clear commit messages
- [ ] PR description complete

**Skills Referenced:**
- code-implementation
- tdd-workflow
- pr-management

---

### 2.3 Orchestration Agent
**File:** `.claude/agents/orchestration.md`
**Model:** sonnet
**Tools:** Read, Write, Edit, Grep, FindByName, ListDir, RunCommand

**Purpose:** Coordinate background operations (webhooks, skills, monitoring)

**Responsibilities:**
1. **Webhook Operations** → Create, edit, delete, test, monitor
2. **Skill Operations** → Upload, update, delete, validate
3. **Agent Operations** → Configure, upload, manage permissions
4. **Database Operations** → Query, reports, cleanup
5. **API Integration** → External API calls, auth handling
6. **Monitoring** → Health checks, event tracking, alerts

**Skills Referenced:**
- webhook-management
- skill-management
- agent-management
- monitoring

**Execution Pattern:**
```
Receive delegation → Select skill → Execute operation → Validate → Report back
```

---

## 3. Skills (Native)

### 3.1 Webhook Management Skill
**Location:** `.claude/skills/webhook-management/SKILL.md`

**Capabilities:**
- Create webhooks with custom configurations
- Edit webhook commands and triggers
- Configure bot mention tags (`@agent`, `@bot`)
- Set up assignee triggers
- Test webhooks before deployment
- Monitor webhook events
- Delete webhooks

**Scripts:**
- `create_webhook.py` - Create new webhook configs
- `edit_command.py` - Edit existing webhook commands
- `test_webhook.py` - Test with sample payloads

**API Endpoints:**
- POST `/api/webhooks` - Create webhook
- PUT `/api/webhooks/{id}` - Update webhook
- POST `/api/webhooks/{id}/commands` - Add command
- PUT `/api/webhooks/{id}/commands/{cmd_id}` - Edit command
- POST `/api/webhooks/{id}/test` - Test webhook
- DELETE `/api/webhooks/{id}` - Delete webhook

**Configuration Options:**
- **Mention Tags:** `@agent`, `@ai-assistant`, `@bot`, custom
- **Assignee Triggers:** AI Agent, automation-bot, custom usernames
- **Trigger Conditions:** Event type, field conditions, pattern matching

**Example Usage:**
```python
# GitHub Mention Webhook
create_webhook(
    provider="github",
    name="GitHub Mentions",
    mention_tags=["@agent", "@bot"],
    commands=[{
        "trigger": "issue_comment.created",
        "condition": "body contains @agent",
        "action": "create_task",
        "agent": "planning"
    }]
)

# Jira Assignee Webhook
create_webhook(
    provider="jira",
    name="Jira Assignee",
    assignee_triggers=["AI Agent"],
    commands=[{
        "trigger": "issues.assigned",
        "condition": "assignee == 'AI Agent'",
        "action": "ask",
        "agent": "brain"
    }]
)
```

---

## 4. Dynamic Agent System

### 4.1 Dynamic Agents (User-Uploaded)

**Storage Location:** `/data/agents/`

**Current Dynamic Agents:**
- **jira-analyzer** (uploaded by user)
  - Location: `/data/agents/jira-analyzer/`
  - Contains: `.claude/`, `README.md`, `skills/`

**Upload Methods:**
1. **Dashboard UI** → Registry → Agents → Upload Agent
2. **API** → POST `/api/registry/agents/upload`

**Agent Structure:**
```
my-agent/
├── .claude/
│   └── CLAUDE.md          # Agent instructions
├── README.md              # Documentation
└── skills/                # Agent-specific skills
```

---

## 5. Persistent Storage (`/data` Volume)

```
/data/
├── agents/                         # Dynamic agents (user-uploaded)
│   └── jira-analyzer/
├── config/                         # Configuration data
│   └── {webhooks,agents,skills}/
├── credentials/                    # Secrets (managed by system)
├── db/                             # SQLite database
├── plans/                          # Generated fix plans
└── registry/                       # Skill/agent registry
```

**Persistence Behavior:**
- All user uploads → `/data/config/` or `/data/agents/`
- Survives container restarts (Docker volume mapping)
- Credentials managed separately (cannot be edited directly)

---

## 6. Business Logic (Pydantic Models)

**File:** `shared/machine_models.py`

All business rules are enforced via Pydantic models:

### 6.1 Task Model
- **Status Transitions:** `QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED`
- Automatic timing and duration calculation
- Cost and token usage tracking

### 6.2 Conversation Model
- **ConversationDB:** Title, user_id, updated_at
- **ConversationMessageDB:** Role, content, metadata
- Automatic context retrieval (last 20 messages)

### 6.3 Session Model
- Tracks total cost and active tasks per user session

### 6.4 Webhook Models
- **WebhookConfig:** Provider, secret, enabled status
- **WebhookCommand:** Trigger, action, template, priority

### 6.5 AgentType Enum
```python
PLANNING = "planning"
EXECUTOR = "executor"
CODE_IMPLEMENTATION = "code_implementation"
QUESTION_ASKING = "question_asking"
CONSULTATION = "consultation"
CUSTOM = "custom"
```

---

## 7. Process Flow

### 7.1 Dashboard Chat Flow
1. User selects/creates **Conversation**
2. User sends message via Dashboard
3. Message saved to `ConversationMessageDB`
4. **Context** (last 20 messages) retrieved
5. **Task** created in SQLite (status=QUEUED)
6. Task ID pushed to **Redis Queue**
7. **TaskWorker** pops task, marks as RUNNING
8. Claude CLI spawned in `/app` with agent context
9. Output streamed real-time via **WebSocket**
10. Task completes; results saved; status updated
11. Response added back to **Conversation**

### 7.2 Unified Webhook Flow
1. Webhook received (e.g., `/webhooks/github/webhook-123`)
2. HMAC signature verified
3. Payload matched against **WebhookCommands**
4. Actions executed in **Priority Order**:
   - `github_reaction` → Add 👀 or 👍
   - `github_label` → Add labels
   - `create_task` → Create agent task
   - `comment` → Post acknowledgment
5. TaskWorker processes created tasks

---

## 8. Key Technologies

**Backend:**
- FastAPI (daemon)
- Pydantic (domain models)
- SQLite (persistent data)
- Redis (task queue + cache)
- Asyncio (all I/O)

**Frontend:**
- WebSocket (real-time streaming)
- Static HTML/JS dashboard

**CLI:**
- Claude Code CLI (spawned on-demand per task)

**Package Management:**
- `uv` (exclusively - NOT pip/poetry)

**Testing:**
- pytest + pytest-asyncio
- Full coverage for business logic

---

## 9. Delegation Pattern (Brain → Subagents)

### How Brain Delegates Tasks

**Natural Language Delegation:**
```
"Use the planning subagent to analyze the authentication bug"
"Use the executor subagent to implement the fix in login.py"
"Use the orchestration subagent to create a GitHub webhook"
```

**Parallel Work:**
```
Use the planning subagent to analyze the auth module
Use the executor subagent to fix the database connection issue (in background)
```

**Sequential Work:**
```
Use the planning subagent to analyze the bug
[Wait for results]
Use the executor subagent to implement the recommended fix
```

**Chain Sub-Agents:**
```
Use the planning subagent to identify performance issues
[Review findings]
Use the executor subagent to optimize the identified bottlenecks
```

---

## 10. Documentation Files

**Total:** 13 markdown files in `/app/docs/`

Key docs:
- `SKILLS-AND-AGENTS-GUIDE.md` - Upload & creation guide
- `UNIFIED-WEBHOOK-SYSTEM.md` - Webhook architecture
- `ORCHESTRATION-AGENT-ARCHITECTURE.md` - Agent coordination
- `CONVERSATION-QUICKSTART.md` - Chat system usage
- `DOCKER-PERSISTENCE-GUIDE.md` - Volume mapping
- `WEBHOOK-SETUP.md` - Webhook configuration
- `MODEL-CONFIGURATION.md` - Model selection
- `NGROK-SETUP.md` - Public webhook URLs
- `CLOUD-DEPLOYMENT-GUIDE.md` - Production deployment

---

## 11. Current Skills vs Subagents

### Built-in Subagents (3)
✅ **planning** - Bug analysis & plan creation
✅ **executor** - Code implementation
✅ **orchestration** - System operations

### Native Skills (1)
✅ **webhook-management** - Webhook lifecycle

### Dynamic Agents (1)
✅ **jira-analyzer** - Jira ticket analysis (user-uploaded)

### Skill Upload Capability
✅ Full dashboard upload support
✅ API upload support
✅ Persistent storage in `/data/config/skills/`
✅ Automatic validation

---

## 12. Brain Capabilities

### Brain CAN:
- Delegate to subagents using natural language
- Create and edit any files in workspace
- Run bash commands
- Read files and logs
- Install packages
- Monitor system health
- Answer questions directly

### Brain CANNOT:
- Modify `/data/credentials/` directly
- Delete critical system files in `/app/.claude/`
- Bypass authentication

---

## 13. Recommendations for Skill/Subagent Creation

### When to Create a Skill
- **Specialized operations** (e.g., data processing, API integration)
- **Reusable tools** (e.g., CSV parser, report generator)
- **Helper scripts** (e.g., deployment automation)

### When to Create a Subagent
- **Complex workflows** (e.g., multi-step analysis)
- **Domain expertise** (e.g., security auditing, performance optimization)
- **Autonomous tasks** (e.g., continuous monitoring, scheduled jobs)

### Skill Structure Best Practices
```
my-skill/
├── SKILL.md                # Required: Description & usage
├── scripts/
│   ├── run.py             # Main script
│   └── helpers.py         # Utilities
└── README.md              # Optional: Extended docs
```

### Subagent Structure Best Practices
```
my-agent/
├── .claude/
│   └── CLAUDE.md          # Agent instructions (role, capabilities, process)
├── skills/                # Agent-specific skills
│   └── custom-skill/
│       └── SKILL.md
└── README.md              # Documentation
```

---

## 14. Next Steps

1. **Explore Dynamic Agent Creation**
   - Review `/data/agents/jira-analyzer/` as example
   - Consider creating specialized agents for common tasks

2. **Expand Skill Library**
   - Create skills for data processing, reporting, monitoring
   - Upload via dashboard or API

3. **Configure Webhooks**
   - Set up GitHub/Jira/Slack integrations
   - Use pre-built templates or create custom triggers

4. **Test End-to-End Flow**
   - Create conversation → Send message → Monitor task execution
   - Test webhook events → Verify task creation → Check results

---

## Conclusion

This container is a **fully-functional orchestration machine** with:
- 3 specialized subagents (Planning, Executor, Orchestration)
- 1 native skill (webhook-management)
- Dynamic agent/skill upload system
- Persistent storage for all configurations
- Real-time dashboard with WebSocket streaming
- Unified webhook system for external integrations

The architecture is **extensible by design** - users can upload custom agents and skills via the dashboard or API, and all configurations persist across container restarts.
