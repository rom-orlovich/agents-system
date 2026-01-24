# Intelligent Code Analysis Workflows Plan

## Issue Summary

Enhance service integration subagents to support end-to-end workflows where:
1. Jira tickets assigned to AI agent trigger automated analysis
2. GitHub subagent analyzes code (clone for complex, API for simple)
3. Results posted back to Jira and draft PRs created when needed
4. Slack notifications sent before/after each Claude Code CLI job

## Root Cause / Current State

The codebase has:
- **Existing clients**: `core/jira_client.py`, `core/github_client.py`, `core/slack_client.py`, `core/sentry_client.py`
- **Existing skills**: `.claude/skills/{jira,github,slack,sentry}-operations/SKILL.md` with CLI commands
- **Task worker**: `workers/task_worker.py` with basic Slack notifications on completion
- **Webhook engine**: `core/webhook_engine.py` with task creation and comment posting

**Gaps identified:**
1. Skills have documentation but lack scripts for Claude CLI to execute
2. No intelligent decision logic for clone vs. API fetch
3. No pre-job Slack notifications (only post-completion)
4. No PR creation automation integrated with Jira
5. No Sentry-to-Jira linking workflow

---

## Business Requirements

| Requirement | Problem Solved | User Story |
|------------|----------------|------------|
| Jira comment posting | Manual status updates | As a developer, I want analysis results posted to Jira automatically |
| GitHub clone vs API | Performance on large repos | As an agent, I want to clone for complex analysis, API for quick checks |
| Draft PR creation | Manual PR creation | As a developer, I want draft PRs created with analysis findings |
| Slack job notifications | Lack of visibility | As a team lead, I want to see when agent jobs start and complete |
| Sentry-Jira linking | Manual error tracking | As an ops engineer, I want Sentry issues linked to Jira tickets |

---

## User Stories

### US1: Jira Ticket Analysis Workflow
**As a** developer  
**I want** the AI agent to analyze my Jira ticket and post findings  
**So that** I get immediate insights without manual investigation

**Acceptance Criteria:**
- [ ] When ticket assigned to agent, analysis starts
- [ ] Analysis results posted as Jira comment (formatted markdown)
- [ ] PR link added to ticket if changes proposed
- [ ] Slack notification sent on start and completion

### US2: Intelligent GitHub Analysis
**As an** AI agent  
**I want** to choose between cloning and API fetch based on task complexity  
**So that** I can analyze efficiently without unnecessary overhead

**Acceptance Criteria:**
- [ ] Simple queries (file lookup, search) use `gh api`
- [ ] Complex analysis (multi-file, deep analysis) clones repo
- [ ] Cloned repos persist in `/data/workspace/repos/`
- [ ] Repos are updated (git pull) before each use

### US3: Pre/Post Job Slack Notifications
**As a** team lead  
**I want** notifications when agent jobs start and complete  
**So that** I have visibility into agent activity

**Acceptance Criteria:**
- [ ] Notification sent when task moves to RUNNING
- [ ] Notification includes: task_id, source, command, agent
- [ ] Completion notification includes: status, summary, cost
- [ ] Notifications go to configurable channel

---

## Responsibility Breakdown

### Domain 1: Skills & Scripts (Claude Code CLI)

**Owner:** Claude Code (executor subagent)  
**Files to create/modify:**

| File | Purpose |
|------|---------|
| `.claude/skills/jira-operations/scripts/post_comment.sh` | Post formatted comment to Jira |
| `.claude/skills/jira-operations/scripts/format_analysis.sh` | Format analysis results for Jira |
| `.claude/skills/github-operations/scripts/analyze_complexity.sh` | Decide clone vs API |
| `.claude/skills/github-operations/scripts/clone_or_fetch.sh` | Clone/update repository |
| `.claude/skills/github-operations/scripts/create_draft_pr.sh` | Create draft PR with analysis |
| `.claude/skills/github-operations/scripts/fetch_files_api.sh` | Fetch files via gh api |
| `.claude/skills/slack-operations/scripts/notify_job_start.sh` | Send job start notification |
| `.claude/skills/slack-operations/scripts/notify_job_complete.sh` | Send job completion notification |
| `.claude/skills/sentry-operations/scripts/analyze_error.sh` | Analyze Sentry error |
| `.claude/skills/sentry-operations/scripts/link_to_jira.sh` | Link Sentry issue to Jira |

### Domain 2: Integration Hooks (Explicit Python Code)

**Owner:** Developer (explicit code)  
**Files to modify:**

| File | Changes |
|------|---------|
| `workers/task_worker.py` | Add pre-job notification hook |
| `core/slack_client.py` | Add `send_job_start_notification()` method |
| `core/jira_client.py` | Add `post_formatted_comment()` with ADF support |
| `core/github_client.py` | Add `should_clone_repository()` heuristic |

### Domain 3: Workflow Documentation

**Owner:** Claude Code (planning subagent)  
**Files to create/modify:**

| File | Purpose |
|------|---------|
| `.claude/skills/jira-operations/workflows/ticket-analysis.md` | End-to-end ticket analysis workflow |
| `.claude/skills/github-operations/workflows/code-analysis.md` | Code analysis decision tree |
| `.claude/skills/sentry-operations/workflows/error-analysis.md` | Sentry error analysis workflow |

---

## Execute Tasks

### Phase 1: Foundation Scripts (Claude Code CLI)

| Task | Agent | Domain | Conf | Verification |
|------|-------|--------|------|--------------|
| Create Jira comment posting script | executor | Skills | 90% | Script runs, posts comment to test ticket |
| Create Jira analysis formatter | executor | Skills | 85% | Markdown/ADF output matches expected format |
| Create GitHub complexity analyzer | executor | Skills | 80% | Returns clone/api decision for test cases |
| Create GitHub clone/fetch script | executor | Skills | 90% | Repo cloned/updated in /data/workspace/repos |
| Create GitHub draft PR script | executor | Skills | 85% | Draft PR created with correct metadata |
| Create GitHub API fetch script | executor | Skills | 90% | Files fetched via gh api |

### Phase 2: Slack Notification Integration

| Task | Agent | Domain | Conf | Verification |
|------|-------|--------|------|--------------|
| Create job start notification script | executor | Skills | 90% | Slack message sent with task info |
| Create job complete notification script | executor | Skills | 90% | Slack message sent with result/cost |
| Add pre-job notification hook to task_worker | executor | Integration | 85% | Notification sent before CLI runs |
| Add SlackClient.send_job_start_notification() | executor | Integration | 90% | Method exists, sends correct payload |

### Phase 3: Sentry Integration

| Task | Agent | Domain | Conf | Verification |
|------|-------|--------|------|--------------|
| Create Sentry error analysis script | executor | Skills | 85% | Script fetches and formats error details |
| Create Sentry-to-Jira linking script | executor | Skills | 80% | Remote link added to Jira ticket |

### Phase 4: Workflow Documentation

| Task | Agent | Domain | Conf | Verification |
|------|-------|--------|------|--------------|
| Document Jira ticket analysis workflow | planning | Documentation | 95% | Workflow markdown complete |
| Document GitHub code analysis workflow | planning | Documentation | 95% | Decision tree documented |
| Document Sentry error analysis workflow | planning | Documentation | 95% | Integration steps documented |

### Phase 5: End-to-End Testing

| Task | Agent | Domain | Conf | Verification |
|------|-------|--------|------|--------------|
| TDD: Test Jira comment posting | executor | Testing | 90% | Tests pass for post_comment |
| TDD: Test GitHub complexity analyzer | executor | Testing | 85% | Tests pass for clone/api decision |
| TDD: Test Slack job notifications | executor | Testing | 90% | Tests pass for start/complete notifications |
| Integration test: Jira→GitHub→PR→Jira flow | executor | Testing | 80% | End-to-end flow works |

---

## Technical Approach

### 1. Jira Comment Script (`post_comment.sh`)

```bash
#!/bin/bash
# Usage: ./post_comment.sh PROJ-123 "Comment text"

ISSUE_KEY="$1"
COMMENT="$2"

# Use jira CLI for commenting
jira issue comment "$ISSUE_KEY" "$COMMENT"
```

### 2. GitHub Complexity Analyzer (`analyze_complexity.sh`)

```bash
#!/bin/bash
# Returns: "clone" or "api" based on task complexity

TASK_DESCRIPTION="$1"

# Simple heuristics:
# - Keywords like "search", "find", "check" → api
# - Keywords like "analyze", "refactor", "implement" → clone
# - File count > 5 → clone
# - Repository size > 100MB → clone (check via gh api)

if echo "$TASK_DESCRIPTION" | grep -qiE "search|find|check|view|get"; then
  echo "api"
elif echo "$TASK_DESCRIPTION" | grep -qiE "analyze|refactor|implement|fix|change|multi"; then
  echo "clone"
else
  echo "api"  # Default to API for simple cases
fi
```

### 3. Pre-Job Notification Hook in task_worker.py

```python
# In _process_task(), before running CLI:
if task_db.source == "webhook":
    await self._send_slack_job_start_notification(task_db)
```

### 4. Slack Job Start Notification

```python
async def _send_slack_job_start_notification(self, task_db: TaskDB) -> bool:
    """Send Slack notification when job starts."""
    source_metadata = json.loads(task_db.source_metadata or "{}")
    webhook_source = source_metadata.get("webhook_source", "unknown")
    command = source_metadata.get("command", "unknown")
    
    message = {
        "channel": os.getenv("SLACK_NOTIFICATION_CHANNEL", "#ai-agent-activity"),
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚀 *Job Started*\n*Source:* {webhook_source}\n*Command:* {command}\n*Task ID:* `{task_db.task_id}`"
                }
            }
        ]
    }
    # Send via Slack API...
```

---

## Test Strategy

### Unit Tests (TDD Red-Green-Refactor)

```
tests/
├── unit/
│   ├── test_jira_scripts.py       # Test Jira script outputs
│   ├── test_github_complexity.py  # Test clone/api decision logic
│   ├── test_slack_notifications.py # Test notification formatting
│   └── test_sentry_analysis.py    # Test error analysis formatting
```

### Integration Tests

```
tests/
├── integration/
│   ├── test_jira_workflow.py      # Test Jira→Analysis→Comment flow
│   ├── test_github_workflow.py    # Test GitHub clone/analyze/PR flow
│   ├── test_slack_notifications.py # Test pre/post job notifications
│   └── test_end_to_end_flow.py    # Test complete Jira→GitHub→PR→Slack flow
```

### TDD Lifecycle Templates

**Jira Comment Posting:**
```
TDD Lifecycle for Jira comment posting:
[RED] Write tests/unit/test_jira_scripts.py::test_post_comment_formats_adf
      → Run pytest (expect failures)
[GREEN] Implement .claude/skills/jira-operations/scripts/post_comment.sh
      → Run pytest (expect passes)
[REFACTOR] Improve script formatting → Run pytest (still passes)
```

**GitHub Complexity Analyzer:**
```
TDD Lifecycle for GitHub complexity analyzer:
[RED] Write tests/unit/test_github_complexity.py::test_analyze_complexity_returns_clone_for_complex
      → Run pytest (expect failures)
[GREEN] Implement .claude/skills/github-operations/scripts/analyze_complexity.sh
      → Run pytest (expect passes)
[REFACTOR] Improve heuristics → Run pytest (still passes)
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Jira API rate limits | High | Cache issue details, batch comments |
| GitHub clone timeout | Medium | Use shallow clone, set timeout |
| Slack notification failures | Low | Non-blocking, log errors only |
| Large repo clone storage | Medium | Clean up old repos, use sparse checkout |
| Sentry API authentication | Medium | Validate token before operations |

---

## Success Criteria

- [ ] Jira subagent posts formatted comments via CLI
- [ ] GitHub subagent intelligently chooses clone vs CLI fetch
- [ ] GitHub subagent creates draft PRs with analysis
- [ ] Slack notifications sent before/after each job
- [ ] Sentry errors can be linked to Jira tickets
- [ ] End-to-end workflow works: Jira → Analysis → GitHub → PR → Jira → Slack

---

## Final Validation

**Verifier Agent:** planning  
**Expected Confidence:** 90%  
**Validation Steps:**

1. Create test Jira ticket assigned to agent
2. Verify analysis starts automatically
3. Verify Slack "Job Started" notification
4. Verify GitHub analysis (clone or API)
5. Verify draft PR created if changes needed
6. Verify analysis results posted to Jira
7. Verify Slack "Job Completed" notification
8. Verify all costs and metrics tracked

---

## Implementation Order

1. **Phase 1** (Foundation): Jira/GitHub scripts - allows manual testing
2. **Phase 2** (Notifications): Slack integration - improves visibility
3. **Phase 3** (Sentry): Error analysis - extends capabilities
4. **Phase 4** (Documentation): Workflow docs - enables team usage
5. **Phase 5** (Testing): TDD tests - ensures reliability

---

## Files to Create

```
.claude/skills/
├── jira-operations/
│   ├── scripts/
│   │   ├── post_comment.sh
│   │   └── format_analysis.sh
│   └── workflows/
│       └── ticket-analysis.md
├── github-operations/
│   ├── scripts/
│   │   ├── analyze_complexity.sh
│   │   ├── clone_or_fetch.sh
│   │   ├── create_draft_pr.sh
│   │   └── fetch_files_api.sh
│   └── workflows/
│       └── code-analysis.md
├── slack-operations/
│   └── scripts/
│       ├── notify_job_start.sh
│       └── notify_job_complete.sh
└── sentry-operations/
    ├── scripts/
    │   ├── analyze_error.sh
    │   └── link_to_jira.sh
    └── workflows/
        └── error-analysis.md

tests/
├── unit/
│   ├── test_jira_scripts.py
│   ├── test_github_complexity.py
│   ├── test_slack_notifications.py
│   └── test_sentry_analysis.py
└── integration/
    ├── test_jira_workflow.py
    ├── test_github_workflow.py
    ├── test_slack_job_notifications.py
    └── test_end_to_end_flow.py
```

---

## Notes for Executor

1. **Use TDD methodology** for all script implementations
2. **Scripts should be executable** (`chmod +x`)
3. **Scripts should use environment variables** for credentials
4. **Python integration code** should have corresponding unit tests
5. **Follow existing patterns** in `core/*.py` for client methods
6. **Slack notifications** should be non-blocking (don't fail task if Slack fails)
7. **GitHub clone** should use `/data/workspace/repos/` for persistence
8. **Jira ADF format** is required for rich text comments
