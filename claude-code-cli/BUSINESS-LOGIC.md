# Business Logic & Flow Diagrams

> **Complete flows and interaction patterns for the Claude Code CLI Agent System**

---

## 📋 Table of Contents

1. [Task Lifecycle](#task-lifecycle)
2. [Planning Agent Flow](#planning-agent-flow)
3. [Executor Agent Flow](#executor-agent-flow)
4. [Command System](#command-system)
5. [Webhook Events](#webhook-events)
6. [Task Types & Actions](#task-types--actions)

---

## 🔄 Task Lifecycle

### Overall Flow

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

### Task Status States

| Status | Description | Next States |
|--------|-------------|-------------|
| `DISCOVERING` | Initial analysis in progress | `PENDING_APPROVAL`, `FAILED` |
| `PENDING_APPROVAL` | Awaiting human approval | `APPROVED`, `REJECTED` |
| `APPROVED` | Approved, queued for execution | `EXECUTING` |
| `EXECUTING` | Implementation in progress | `COMPLETED`, `FAILED` |
| `COMPLETED` | Successfully completed | - |
| `FAILED` | Failed (can be requeued) | `DISCOVERING`, `EXECUTING` |
| `REJECTED` | Rejected by human | - |

---

## 🔍 Planning Agent Flow

### Process Overview

```python
# agents/planning-agent/worker.py

async def process_task(self, task: AnyTask):
    """Process planning task with full repository context."""

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

    # 4. Route to appropriate skill based on task type
    if isinstance(task, JiraTask) and task.action == "enrich":
        await self.run_skill("jira-enrichment", task, working_dir, project_rules)
    elif isinstance(task, SentryTask):
        await self.run_skill("discovery", task, working_dir, project_rules)
    elif isinstance(task, GitHubTask) and task.action == "improve":
        await self.run_skill("plan-changes", task, working_dir, project_rules)
    elif task.status == TaskStatus.APPROVED:
        await self.run_skill("execution", task, working_dir, project_rules)

    # 5. Update task status and notify
    await self.queue.update_task_status(task.task_id, TaskStatus.PENDING_APPROVAL)
    await self.run_skill("notifications", task)
```

### Skill Execution Flow

```
Planning Agent Task
        │
        ├─► JiraTask(action="enrich")
        │   └─► skill: jira-enrichment
        │       ├─ scripts/jira_client.py → Get Jira details
        │       ├─ scripts/sentry_fetcher.py → Get linked Sentry data
        │       └─ MCP: atlassian.update_issue → Add analysis to Jira
        │
        ├─► SentryTask
        │   └─► skill: discovery
        │       ├─ scripts/sentry_client.py → Get error details
        │       ├─ scripts/github_search.py → Find affected files
        │       └─ MCP: github.search_code → Search codebase
        │
        ├─► GitHubTask(action="improve")
        │   └─► skill: plan-changes
        │       └─ MCP: github.get_pr → Read feedback + update plan
        │
        └─► Task(status=APPROVED)
            └─► skill: execution
                └─ Create PLAN.md + Draft PR
```

### Repository Cloning (NEW)

The Planning Agent now clones the full repository to get complete context:

```python
def _get_repository(self, task: AnyTask) -> str | None:
    """Extract repository from task."""
    if isinstance(task, (GitHubTask, JiraTask)) and hasattr(task, 'repository'):
        return task.repository
    elif isinstance(task, SentryTask):
        # Look up from Redis mapping (sentry_id → repo)
        return self.queue.get_sentry_repo_mapping(task.sentry_issue_id)
    return None

def _read_project_claude_md(self, working_dir: str) -> str | None:
    """Read project-specific CLAUDE.md file if exists."""
    claude_md_path = os.path.join(working_dir, "CLAUDE.md")
    if os.path.exists(claude_md_path):
        with open(claude_md_path, 'r') as f:
            return f.read()
    return None
```

---

## ⚙️ Executor Agent Flow

### Process Overview

```python
# agents/executor-agent/worker.py

async def process_task(self, task: AnyTask):
    """Process execution task with TDD workflow."""

    # 1. Clone repository
    repo = GitRepository.from_full_name(task.repository)
    await self.git.clone_repository(repo)
    working_dir = self.git.get_repo_path(repo)

    # 2. Read project's CLAUDE.md for project-specific rules
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

    # 8. Update status
    await self.queue.update_task_status(task.task_id, TaskStatus.COMPLETED)
```

### TDD Workflow Detail

```
RED Phase
    ├─► skill: tdd-workflow (run_tests)
    │   ├─ scripts/test_runner.py → Detect test framework
    │   ├─ Run existing tests
    │   └─ Return: TestResult(passed=X, failed=Y)
    │
GREEN Phase
    ├─► skill: execution
    │   ├─ Read PLAN.md
    │   ├─ Implement fix
    │   └─ MCP: filesystem.write_file
    │
VERIFY Phase
    ├─► skill: tdd-workflow (run_tests)
    │   └─ Ensure all tests pass
    │
REVIEW Phase
    ├─► skill: code-review
    │   ├─ scripts/lint_runner.py → Run linters
    │   └─ Return: LintResult(errors=[], warnings=[])
    │
COMMIT Phase
    └─► skill: git-operations
        ├─ scripts/git_utils.py → Commit + push
        └─ skill: github-pr → Update PR status
```

---

## 💬 Command System

### Command Routing by Platform

| Command | Aliases | Platform Support | Handler |
|---------|---------|-----------------|---------|
| `@agent approve` | `lgtm`, `ship-it`, `go` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_approve` |
| `@agent reject [reason]` | `no`, `stop`, `cancel` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_reject` |
| `@agent improve <feedback>` | `refine`, `update`, `fix-plan` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_improve` |
| `@agent status` | `?`, `check`, `info` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_status` |
| `@agent help [cmd]` | `commands`, `usage` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_help` |
| `@agent ci-status` | `ci`, `checks`, `build` | ✅ GitHub, ✅ Slack | `handle_ci_status` |
| `@agent ci-logs` | `why-failed`, `show-error` | ✅ GitHub, ✅ Slack | `handle_ci_logs` |
| `@agent retry-ci` | `rerun`, `rebuild` | ✅ GitHub, ✅ Slack | `handle_retry_ci` |
| `@agent ask <question>` | `how`, `what`, `why` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_ask` |
| `@agent explain <target>` | `describe`, `what-is` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_explain` |
| `@agent find <pattern>` | `grep`, `search` | ✅ GitHub, ✅ Slack | `handle_find` |
| `@agent discover [repo]` | `scan`, `analyze-error` | ✅ GitHub, ✅ Jira, ✅ Slack | `handle_discover` |
| `@agent update-title <title>` | `rename`, `title` | ✅ GitHub only | `handle_update_title` |
| `@agent add-tests` | `write-tests` | ✅ GitHub only | `handle_add_tests` |
| `@agent fix-lint` | `lint`, `format` | ✅ GitHub only | `handle_fix_lint` |
| `@agent update-jira` | `sync-jira` | ✅ GitHub, ✅ Jira | `handle_update_jira` |
| `@agent link-pr <key>` | `attach-pr` | ✅ GitHub only | `handle_link_pr` |

### Command Processing Flow

```
User Comment/Message
        │
        ▼
Parse Command (commands/parser.py)
        ├─► Extract command type
        ├─► Extract arguments
        └─► Validate platform
        │
        ▼
Execute Command (commands/executor.py)
        ├─► Load handler from definitions.yaml
        ├─► Validate permissions
        ├─► Execute handler
        │   ├─► Update task status
        │   ├─► Push to queue (if needed)
        │   └─► Generate response
        │
        ▼
Post Response
        ├─► GitHub: Add comment + reaction
        ├─► Jira: Add comment (ADF format)
        └─► Slack: Reply in thread
```

---

## 🔔 Webhook Events

### GitHub Webhooks

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

### Jira Webhooks

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

### Slack Webhooks

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

### Sentry Webhooks

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

## 📦 Task Types & Actions

### JiraTask Actions

| Action | Trigger | Processing |
|--------|---------|------------|
| `enrich` | Sentry ticket created | Planning agent → Discovery → Update Jira |
| `fix` | Manual request (label/assignment) | Planning agent → Plan → Create PR |
| `approve` | Status transition to Approved | Executor agent → Implement → Push |

**JiraTask Model:**
```python
class JiraTask(BaseModel):
    task_id: str
    jira_issue_key: str
    action: Literal["enrich", "fix", "approve"]
    repository: str | None
    sentry_issue_id: str | None
    description: str
    status: TaskStatus
```

### SentryTask

| Field | Source |
|-------|--------|
| `sentry_issue_id` | `payload.id` |
| `description` | `event.message` or `payload.title` |
| `repository` | From `repository` tag in event |

**SentryTask Model:**
```python
class SentryTask(BaseModel):
    task_id: str
    sentry_issue_id: str
    description: str
    repository: str
    stack_trace: str | None
    status: TaskStatus
```

### GitHubTask

| Field | Source |
|-------|--------|
| `repository` | `payload.repository.full_name` |
| `pr_number` | `payload.issue.number` or `payload.pull_request.number` |
| `pr_url` | `payload.issue.html_url` |
| `action` | Command type (approve, improve, etc) |
| `comment` | Comment body for improve commands |

**GitHubTask Model:**
```python
class GitHubTask(BaseModel):
    task_id: str
    repository: str
    pr_number: int
    pr_url: str
    action: str
    comment: str | None
    status: TaskStatus
```

---

## 🔧 Skill Scripts

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

**Last Updated**: January 2026
**Version**: 1.0.0
