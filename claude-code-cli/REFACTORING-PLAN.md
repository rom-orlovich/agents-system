# Comprehensive Refactoring Plan

## 🎯 Goal

Transform the codebase into a modular, production-ready, cloud-native system that is:
- Easy to maintain and extend
- Clean and readable
- Well-tested with TDD
- Ready for separate repository deployment

---

## 📋 Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [New Directory Structure](#new-directory-structure)
3. [Skills Mapping](#skills-mapping)
4. [Business Logic Flow](#business-logic-flow)
5. [Implementation Phases](#implementation-phases)
6. [File Migration Guide](#file-migration-guide)

---

## 📊 Current State Analysis

### Existing Skills (8 total)

| Agent | Skill | Purpose |
|-------|-------|---------|
| **Planning** | `discovery/` | Find affected repos and files |
| **Planning** | `jira-enrichment/` | Enrich Jira tickets with analysis |
| **Planning** | `plan-changes/` | Update plans based on feedback |
| **Planning** | `execution/` | Execute approved plans |
| **Executor** | `git-operations/` | Git workflow (clone, branch, commit, push) |
| **Executor** | `tdd-workflow/` | RED → GREEN → REFACTOR cycle |
| **Executor** | `execution/` | Main orchestration |
| **Executor** | `code-review/` | Self-review before commit |

### Current Shared Modules

| Module | Lines | Can Become Skill Scripts? |
|--------|-------|---------------------------|
| `git_utils.py` | 648 | ✅ Yes → `git-operations/scripts/` |
| `github_client.py` | 202 | ✅ Yes → `discovery/scripts/`, `execution/scripts/` |
| `slack_client.py` | 318 | ✅ Yes → `notifications/` skill |
| `token_manager.py` | 524 | 🔶 Keep as shared utility |
| `claude_runner.py` | 489 | 🔶 Keep as shared utility |
| `task_queue.py` | 397 | 🔶 Keep as client |
| `database.py` | 150 | 🔶 Keep as client |
| `commands/` | ~1100 | 🔶 Keep as module |

---

## 📁 New Directory Structure

```
claude-agent-system/
├── pyproject.toml
├── Makefile
├── docker-compose.yml
├── .env.example
│
├── README.md
├── ARCHITECTURE.md
├── BUSINESS-LOGIC.md              # NEW: Define all flows
│
├── config/
│   ├── __init__.py
│   ├── settings.py                # Pydantic Settings
│   └── constants.py               # Static constants only
│
├── models/
│   ├── __init__.py
│   ├── tasks.py                   # BaseTask, JiraTask, etc.
│   ├── git.py                     # GitRepository, GitOperationResult
│   ├── auth.py                    # OAuthCredentials
│   ├── commands.py                # Command models
│   └── results.py                 # TestResult, LintResult
│
├── types/
│   ├── __init__.py
│   └── enums.py                   # All enums
│
├── clients/
│   ├── __init__.py
│   ├── redis_queue.py             # Task queue operations
│   └── database.py                # DB operations
│
├── utils/
│   ├── __init__.py
│   ├── claude.py                  # Claude runner (shared)
│   ├── token.py                   # Token manager (shared)
│   ├── logging.py                 # Logging setup
│   └── metrics.py                 # Prometheus metrics
│
├── commands/
│   ├── __init__.py
│   ├── parser.py
│   ├── executor.py
│   ├── loader.py
│   └── definitions.yaml
│
├── workers/
│   ├── __init__.py
│   └── base.py                    # BaseAgentWorker
│
├── agents/
│   ├── planning/
│   │   ├── Dockerfile
│   │   ├── entrypoint.sh
│   │   ├── main.py
│   │   ├── worker.py
│   │   └── skills/
│   │       ├── discovery/
│   │       │   ├── SKILL.md
│   │       │   └── scripts/
│   │       │       ├── github_search.py
│   │       │       └── sentry_client.py
│   │       ├── jira-enrichment/
│   │       │   ├── SKILL.md
│   │       │   └── scripts/
│   │       │       └── jira_client.py
│   │       ├── plan-changes/
│   │       │   └── SKILL.md
│   │       └── notifications/              # NEW SKILL
│   │           ├── SKILL.md
│   │           └── scripts/
│   │               └── slack_client.py
│   │
│   └── executor/
│       ├── Dockerfile
│       ├── entrypoint.sh
│       ├── main.py
│       ├── worker.py
│       └── skills/
│           ├── git-operations/
│           │   ├── SKILL.md
│           │   └── scripts/
│           │       └── git_utils.py          # From shared/
│           ├── tdd-workflow/
│           │   ├── SKILL.md
│           │   └── scripts/
│           │       └── test_runner.py
│           ├── execution/
│           │   └── SKILL.md
│           ├── code-review/
│           │   ├── SKILL.md
│           │   └── scripts/
│           │       └── lint_runner.py
│           └── github-pr/                    # NEW SKILL
│               ├── SKILL.md
│               └── scripts/
│                   └── github_client.py      # From shared/
│
├── services/
│   ├── webhook_server/
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── routes/
│   │       ├── github.py
│   │       ├── jira.py
│   │       ├── sentry.py
│   │       └── slack.py
│   │
│   └── dashboard/
│       ├── main.py
│       ├── Dockerfile
│       └── static/
│
├── scripts/
│   ├── refresh_token.py
│   ├── create_task.py
│   └── requeue_task.py
│
├── scripts/dev/                   # Development only
│   ├── seed_db.py
│   └── demo_approval_flow.py
│
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_commands.py
    │   ├── test_models.py
    │   ├── test_queue.py
    │   └── test_business_logic.py
    └── integration/
        ├── test_webhooks.py
        └── test_workers.py
```

---

## 🔧 Skills Mapping

### Planning Agent Skills

#### 1. `discovery/` - Repository Discovery
```
Purpose: Find affected repos and files from errors
Scripts:
├── scripts/github_search.py     # Search code in GitHub
├── scripts/sentry_client.py     # Fetch Sentry issue details
└── scripts/file_analyzer.py     # Analyze file structure
```

#### 2. `jira-enrichment/` - Jira Ticket Enrichment
```
Purpose: Enrich Jira tickets with analysis
Scripts:
├── scripts/jira_client.py       # Jira API operations
└── scripts/sentry_fetcher.py    # Get linked Sentry data
```

#### 3. `plan-changes/` - Plan Updates
```
Purpose: Update plans based on PR feedback
Scripts:
└── scripts/pr_analyzer.py       # Analyze PR comments
```

#### 4. `notifications/` - **NEW SKILL**
```
Purpose: Send notifications to Slack
Scripts:
└── scripts/slack_client.py      # Slack API wrapper
```

### Executor Agent Skills

#### 1. `git-operations/` - Git Workflow
```
Purpose: All Git operations (clone, branch, commit, push)
Scripts:
└── scripts/git_utils.py         # From shared/git_utils.py
                                  # (simplified, CLI-focused version)
```

#### 2. `tdd-workflow/` - Test-Driven Development
```
Purpose: RED → GREEN → REFACTOR cycle
Scripts:
├── scripts/test_runner.py       # Run tests (detect framework)
└── scripts/test_analyzer.py     # Parse test results
```

#### 3. `code-review/` - Code Quality
```
Purpose: Self-review before commit
Scripts:
├── scripts/lint_runner.py       # Run linters
└── scripts/type_checker.py      # Run type checking
```

#### 4. `github-pr/` - **NEW SKILL**
```
Purpose: GitHub PR operations
Scripts:
├── scripts/github_client.py     # From shared/github_client.py
└── scripts/pr_creator.py        # Create/update PRs
```

---

## 🔄 Business Logic Flow

### 1. Task Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                        TASK LIFECYCLE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Webhook    ──►  Redis Queue  ──►  Planning Agent               │
│  (Trigger)       (planning_q)      │                            │
│                                    ├─► Clone Repo               │
│                                    ├─► Read Project CLAUDE.md   │
│                                    ├─► Run Discovery/Analysis   │
│                                    ├─► Create PLAN.md           │
│                                    └─► Open Draft PR            │
│                                         │                       │
│                                         ▼                       │
│                                    PENDING_APPROVAL             │
│                                         │                       │
│                                         ▼                       │
│  @agent approve  ──►  Webhook  ──►  Update Status               │
│  (GitHub/Slack)                    ──►  APPROVED                │
│                                         │                       │
│                                         ▼                       │
│                                    Redis Queue                  │
│                                    (execution_q)                │
│                                         │                       │
│                                         ▼                       │
│                                    Executor Agent               │
│                                    │                            │
│                                    ├─► Clone Repo               │
│                                    ├─► Read Project CLAUDE.md   │
│                                    ├─► Run Tests (RED)          │
│                                    ├─► Implement Fix (GREEN)    │
│                                    ├─► Run Tests (verify)       │
│                                    ├─► Commit & Push            │
│                                    └─► Update PR                │
│                                         │                       │
│                                         ▼                       │
│                                    COMPLETED                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Planning Agent Flow (with Repo Cloning)

```python
# agents/planning/worker.py

async def process_task(self, task: AnyTask):
    """Process planning task."""
    
    # 1. Get repository from task
    repository = self._get_repository(task)
    
    # 2. Clone repository for full context (NEW!)
    if repository:
        repo = GitRepository.from_full_name(repository)
        result = await self.git.clone_repository(repo)
        working_dir = self.git.get_repo_path(repo)
        
        # 3. Read project's CLAUDE.md if exists (NEW!)
        project_rules = self._read_project_claude_md(working_dir)
    else:
        working_dir = AGENT_DIR
        project_rules = None
    
    # 4. Route to appropriate skill
    if isinstance(task, JiraTask) and task.action == "enrich":
        await self.run_skill("jira-enrichment", task, working_dir, project_rules)
    elif isinstance(task, SentryTask):
        await self.run_skill("discovery", task, working_dir, project_rules)
    # ...
```

### 3. Executor Agent Flow

```python
# agents/executor/worker.py

async def process_task(self, task: AnyTask):
    """Process execution task."""
    
    # 1. Clone repository
    repo = GitRepository.from_full_name(task.repository)
    await self.git.clone_repository(repo)
    working_dir = self.git.get_repo_path(repo)
    
    # 2. Read project's CLAUDE.md
    project_rules = self._read_project_claude_md(working_dir)
    
    # 3. Create feature branch
    branch = f"fix/{task.task_id}"
    await self.git.create_branch(working_dir, branch)
    
    # 4. Run TDD workflow
    # RED: Run initial tests (expect some failures)
    initial_tests = await self.run_skill("tdd-workflow", "run_tests", working_dir)
    
    # GREEN: Implement fix
    await self.run_skill("execution", task, working_dir, project_rules)
    
    # VERIFY: Run tests again
    final_tests = await self.run_skill("tdd-workflow", "run_tests", working_dir)
    
    # 5. Code review
    await self.run_skill("code-review", working_dir)
    
    # 6. Commit and push
    await self.run_skill("git-operations", "commit_and_push", working_dir, branch)
    
    # 7. Update PR
    await self.run_skill("github-pr", "update_pr", task.pr_url)
```

---

## � Commands & Business Logic by Platform

### GitHub Commands

| Command | Aliases | Platform Support | Handler | Description |
|---------|---------|-----------------|---------|-------------|
| `@agent approve` | `lgtm`, `ship-it`, `go` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_approve` | Approve plan and start execution |
| `@agent reject [reason]` | `no`, `stop`, `cancel` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_reject` | Reject plan with optional reason |
| `@agent improve <feedback>` | `refine`, `update`, `fix-plan` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_improve` | Request plan improvements |
| `@agent status` | `?`, `check`, `info` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_status` | Get task status |
| `@agent help [cmd]` | `commands`, `usage` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_help` | Show help text |
| `@agent ci-status` | `ci`, `checks`, `build` | ✅ GitHub, ✅ Slack | `handle_ci_status` | Check CI/CD status |
| `@agent ci-logs` | `why-failed`, `show-error` | ✅ GitHub, ✅ Slack | `handle_ci_logs` | Get CI failure logs |
| `@agent retry-ci` | `rerun`, `rebuild` | ✅ GitHub, ✅ Slack | `handle_retry_ci` | Re-run failed CI |
| `@agent ask <question>` | `how`, `what`, `why` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_ask` | Ask about codebase |
| `@agent explain <target>` | `describe`, `what-is` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_explain` | Explain file/function |
| `@agent find <pattern>` | `grep`, `search` | ✅ GitHub, ✅ Slack | `handle_find` | Search in codebase |
| `@agent discover [repo]` | `scan`, `analyze-error` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_discover` | Find affected files |
| `@agent update-title <title>` | `rename`, `title` | ✅ GitHub only | `handle_update_title` | Update PR title |
| `@agent add-tests` | `write-tests` | ✅ GitHub only | `handle_add_tests` | Add tests for changes |
| `@agent fix-lint` | `lint`, `format` | ✅ GitHub only | `handle_fix_lint` | Auto-fix lint issues |
| `@agent update-jira` | `sync-jira` | ✅ GitHub, ✅ Jira | `handle_update_jira` | Update linked Jira |
| `@agent link-pr <key>` | `attach-pr` | ✅ GitHub only | `handle_link_pr` | Link PR to Jira |

---

### GitHub Webhook Events

| Event | Trigger | Action |
|-------|---------|--------|
| `issue_comment` (action=created) | PR comment with bot mention | Parse command → Execute → React |
| `pull_request_review` (state=approved) | PR approval by reviewer | Auto-approve task → Push to execution queue |
| `push` | Push to branch | Log (potential CI trigger) |

**GitHub Webhook Flow:**
```
PR Comment  →  validate_signature  →  parse_command  →  execute_command
     │                                      │              │
     └──────► add "eyes" reaction           │              └──► add "rocket" or "confused" reaction
                                            │
                                            └──► post reply comment if result.should_reply
```

---

### Jira Webhook Events

| Event | Condition | Action | Queue |
|-------|-----------|--------|-------|
| `jira:issue_created` | Sentry ticket OR assigned to bot | Create `JiraTask(action="enrich")` | `planning_queue` |
| `jira:issue_created` | Has "AI-Fix" label | Create `JiraTask(action="fix")` | `planning_queue` |
| `jira:issue_updated` | Status → "Approved" or "In Progress" | Create `JiraTask(action="approve")` | `execution_queue` |
| `jira:issue_updated` | Assigned to bot | Create `JiraTask(action="fix")` | `planning_queue` |

**Jira Webhook Flow:**
```
Jira Event  →  extract_sentry_issue_id  →  extract_repository
     │                │                         │
     │                └── from description        └── from description OR Redis mapping
     │
     ├── is_sentry_ticket?  →  JiraTask(action="enrich")  →  planning_queue
     ├── assigned_to_bot?   →  JiraTask(action="fix")     →  planning_queue  + post_jira_comment
     └── status="Approved"? →  JiraTask(action="approve") →  execution_queue
```

**Jira Extraction Functions:**
- `extract_sentry_issue_id(description)` → Parse "Sentry Issue: [ID](url)" pattern
- `extract_repository_from_description(description)` → Parse "github.com/owner/repo" or "Repository: owner/repo"
- `post_jira_comment(issue_key, message)` → Post ADF comment to Jira issue

---

### Slack Webhook Events

| Event | Trigger | Action |
|-------|---------|--------|
| `url_verification` | Slack challenge | Return challenge value |
| `block_actions` (approve_task) | Click "Approve" button | Update status → Push to execution queue |
| `block_actions` (reject_task) | Click "Reject" button | Update status to REJECTED |
| `app_mention` | @bot in channel | Parse command → Execute → Reply in thread |
| `message` (DM) | Direct message to bot | Parse command → Execute → Reply |

**Slack Webhook Flow:**
```
Slack Event  →  parse_event_type
     │
     ├── url_verification  →  return { challenge }
     │
     ├── block_actions (button)
     │        ├── approve_task  →  update_status(APPROVED)  →  push_to_execution_queue
     │        └── reject_task   →  update_status(REJECTED)
     │
     ├── app_mention  →  normalize_text  →  parse_command  →  execute
     │        └──► add_reaction  →  reply_in_thread
     │
     └── message (DM)  →  prepend "@agent"  →  parse_command  →  execute
```

---

### Sentry Webhook Events

| Event | Action |
|-------|--------|
| `issue.alert` | Extract tags → Create `SentryTask` → Store sentry→repo mapping → Push to planning queue |

**Sentry Webhook Flow:**
```
Sentry Alert  →  extract_sentry_tags  →  get "repository" tag
     │                                         │
     │                                         └── SentryTask(sentry_issue_id, repository)
     │
     └── store_sentry_repo_mapping(sentry_id, repo)  # For later Jira lookup
```

---

## 🧩 Task Types & Actions

### JiraTask Actions

| Action | Trigger | Processing |
|--------|---------|------------|
| `enrich` | Sentry ticket created | Planning agent → Discovery → Update Jira |
| `fix` | Manual request (label/assignment) | Planning agent → Plan → Create PR |
| `approve` | Status transition to Approved | Executor agent → Implement → Push |

### SentryTask

| Field | Source |
|-------|--------|
| `sentry_issue_id` | `payload.id` |
| `description` | `event.message` or `payload.title` |
| `repository` | From `repository` tag in event |

### GitHubTask

| Field | Source |
|-------|--------|
| `repository` | `payload.repository.full_name` |
| `pr_number` | `payload.issue.number` or `payload.pull_request.number` |
| `pr_url` | `payload.issue.html_url` |
| `action` | Command type (approve, improve, etc) |
| `comment` | Comment body for improve commands |

---

## 📝 Skills That Should Have Scripts

Based on the business logic above, each skill should have scripts for:

### Planning Agent Skills

| Skill | Required Scripts | Purpose |
|-------|------------------|---------|
| `discovery/` | `github_search.py` | Search code with GitHub API |
| | `sentry_client.py` | Fetch Sentry issue details |
| `jira-enrichment/` | `jira_client.py` | Read/update Jira issues |
| | `sentry_fetcher.py` | Get linked Sentry data |
| `notifications/` | `slack_client.py` | Send Slack messages |

### Executor Agent Skills

| Skill | Required Scripts | Purpose |
|-------|------------------|---------|
| `git-operations/` | `git_utils.py` | Clone, branch, commit, push |
| `github-pr/` | `github_client.py` | Create/update PRs, add comments |
| `tdd-workflow/` | `test_runner.py` | Detect and run tests |
| `code-review/` | `lint_runner.py` | Run linters |

---

## 🚀 Implementation Phases

### Phase 1: Documentation (Day 1)
- [ ] Update ARCHITECTURE.md with new structure
- [ ] Create BUSINESS-LOGIC.md with flow diagrams
- [ ] Document all skills and their scripts
- [ ] Define interfaces between components

### Phase 2: TDD - Write Tests First (Day 2-3)
- [ ] `tests/unit/test_business_logic.py` - Task lifecycle
- [ ] `tests/unit/test_planning_flow.py` - Planning agent flow
- [ ] `tests/unit/test_executor_flow.py` - Executor agent flow
- [ ] `tests/unit/test_approval_flow.py` - Approval commands
- [ ] **NO implementation changes yet!**

### Phase 3: Cleanup (Day 4)
- [ ] Delete debug scripts:
  - `services/dashboard/debug_redis.py`
  - `services/dashboard/debug_redis_v2.py`
  - `services/dashboard/write_redis.py`
- [ ] Move dev scripts:
  - `services/dashboard/seed_db.py` → `scripts/dev/`
  - `scripts/demo_approval_flow.py` → `scripts/dev/`

### Phase 4: Restructure Shared (Day 5-6)
- [ ] Create flat module structure:
  - `config/` - Settings and constants
  - `models/` - Pydantic models
  - `types/` - Enums
  - `clients/` - Redis, DB clients
  - `utils/` - Claude runner, logging
  - `commands/` - Bot commands
  - `workers/` - Base worker

### Phase 5: Skills + Scripts (Day 7-8)
- [ ] Create `scripts/` folder in each skill
- [ ] Migrate relevant code:
  - `git_utils.py` → `git-operations/scripts/`
  - `github_client.py` → `discovery/scripts/` + `github-pr/scripts/`
  - `slack_client.py` → `notifications/scripts/`
- [ ] Create new skills:
  - `notifications/` for Planning Agent
  - `github-pr/` for Executor Agent

### Phase 6: Planning Agent Clone (Day 9)
- [ ] Update planning worker to clone repos
- [ ] Add project CLAUDE.md reading
- [ ] Test with real tasks

### Phase 7: Production Polish (Day 10)
- [ ] Fix exception handling
- [ ] Add proper logging
- [ ] Update pyproject.toml
- [ ] Update Dockerfiles
- [ ] Final testing

---

## 📦 File Migration Guide

### From `shared/` to Skills Scripts

| Source File | Target Location | Notes |
|-------------|-----------------|-------|
| `shared/git_utils.py` | `executor/skills/git-operations/scripts/git_utils.py` | Simplify, CLI focus |
| `shared/github_client.py` | `planning/skills/discovery/scripts/github_client.py` | Copy to both |
| `shared/github_client.py` | `executor/skills/github-pr/scripts/github_client.py` | Copy to both |
| `shared/slack_client.py` | `planning/skills/notifications/scripts/slack_client.py` | Move |

### From `shared/` to Core Modules

| Source File | Target Location | Notes |
|-------------|-----------------|-------|
| `shared/config.py` | `config/settings.py` | Keep as-is |
| `shared/constants.py` | `config/constants.py` | Clean up |
| `shared/models.py` | `models/*.py` | Split into files |
| `shared/enums.py` | `types/enums.py` | Keep as-is |
| `shared/task_queue.py` | `clients/redis_queue.py` | Keep as-is |
| `shared/database.py` | `clients/database.py` | Keep as-is |
| `shared/claude_runner.py` | `utils/claude.py` | Keep as-is |
| `shared/token_manager.py` | `utils/token.py` | Keep as-is |
| `shared/commands/` | `commands/` | Keep as module |

---

## ✅ Verification Checklist

### After Each Phase

- [ ] All existing tests pass
- [ ] Docker builds successfully
- [ ] Services start without errors
- [ ] Webhook endpoints respond
- [ ] Agents can process test tasks

### Final Verification

- [ ] Full task lifecycle works (webhook → agent → PR)
- [ ] Approval flow works (@agent approve)
- [ ] Planning agent clones repos
- [ ] Executor agent runs TDD
- [ ] Skills scripts are accessible
- [ ] Notifications sent to Slack
- [ ] Dashboard shows metrics

---

## 📝 Notes

### Key Design Decisions

1. **Flat structure (no `src/`)** - Simpler imports, standard Python packaging
2. **Scripts near skills** - Each skill has its own utilities, not dependent on MCP only
3. **Planning agent clones repos** - Full context for better analysis
4. **Base worker class** - Reduce code duplication between agents
5. **TDD first** - Write tests before implementation changes

### Files to Keep in `shared/` (as compatibility layer)

During migration, keep `shared/__init__.py` that re-exports from new locations:

```python
# shared/__init__.py (temporary compatibility)
from config import settings
from models import *
from types import *
```

This allows gradual migration without breaking imports.

---

*Created: 2026-01-21*
*Last Updated: 2026-01-21*
