# Multi-Subagent Orchestration System - Comprehensive Plan

## Executive Summary

This document outlines a comprehensive architecture for Claude Code to manage multiple subagents, execute tasks autonomously, control its container environment via webhook routes, create new subagents/skills dynamically, and ensure data persistence.

---

## Part 1: Current State Analysis

### Existing Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         BRAIN AGENT                              │
│                    (.claude/CLAUDE.md)                          │
│         Central intelligence - analyzes & delegates             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   PLANNING      │ │   EXECUTOR      │ │  ORCHESTRATION  │
│   (.claude/     │ │   (.claude/     │ │   (.claude/     │
│   agents/       │ │   agents/       │ │   agents/       │
│   planning.md)  │ │   executor.md)  │ │   orchestration │
│                 │ │                 │ │   .md)          │
│ - Analysis      │ │ - Code changes  │ │ - Webhooks      │
│ - PLAN.md       │ │ - TDD workflow  │ │ - Skills mgmt   │
│ - Investigation │ │ - PR creation   │ │ - Agent config  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Current Persistence Layer

| Component | Storage | Persistence |
|-----------|---------|-------------|
| Tasks | SQLite (`/data/db/machine.db`) + Redis | ✅ Persisted |
| Sessions | SQLite | ✅ Persisted |
| Webhooks | SQLite (`WebhookConfigDB`, `WebhookCommandDB`) | ✅ Persisted |
| Webhook Events | SQLite (`WebhookEventDB`) | ✅ Persisted |
| Conversations | SQLite (`ConversationDB`) | ✅ Persisted |
| User Agents | `/data/config/agents/` | ✅ Persisted (volume) |
| User Skills | `/data/config/skills/` | ✅ Persisted (volume) |
| Built-in Agents | `.claude/agents/*.md` | ❌ Image-only |
| Built-in Skills | `.claude/skills/` | ❌ Image-only |
| Task Queue | Redis | ⚠️ Volatile (TTL) |
| Task Output | Redis | ⚠️ Volatile (1hr TTL) |

### Current Webhook Routes

- `POST /webhooks/github` - GitHub events (issues, PRs, comments)
- `POST /webhooks/jira` - Jira issue events
- `POST /webhooks/sentry` - Sentry error events

---

## Part 2: Multi-Subagent Orchestration Architecture

### 2.1 Enhanced Architecture Vision

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BRAIN AGENT                                     │
│                         (Central Orchestrator)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Capabilities:                                                        │   │
│  │ - Analyze user requests                                              │   │
│  │ - Spawn/stop subagents dynamically                                   │   │
│  │ - Create new agents & skills                                         │   │
│  │ - Manage container operations                                        │   │
│  │ - Self-improvement via meta-skills                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  FOREGROUND   │         │  BACKGROUND   │         │   PARALLEL    │
│  SUBAGENTS    │         │  SUBAGENTS    │         │   SWARM       │
│               │         │               │         │               │
│ - Interactive │         │ - Async tasks │         │ - Multi-task  │
│ - User Q&A    │         │ - Long-running│         │ - Concurrent  │
│ - Permissions │         │ - Auto-deny   │         │ - Isolated    │
└───────────────┘         └───────────────┘         └───────────────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
            ┌─────────────┐             ┌─────────────┐
            │   WEBHOOK   │             │  CONTAINER  │
            │   ENGINE    │             │  MANAGER    │
            │             │             │             │
            │ - Triggers  │             │ - Docker    │
            │ - Commands  │             │ - Processes │
            │ - Routing   │             │ - Resources │
            └─────────────┘             └─────────────┘
```

### 2.2 Subagent Execution Modes

Based on Claude Code documentation:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Foreground** | Blocks main conversation, passes permissions/questions | Interactive tasks, user approval needed |
| **Background** | Runs concurrently, auto-denies permissions | Long-running tasks, parallel research |
| **Parallel Swarm** | Multiple background agents simultaneously | Multi-repo analysis, bulk operations |

### 2.3 Native Claude Code Subagent Features

From official docs:
- **Automatic delegation** based on `description` field
- **Tool restrictions** via `tools` and `disallowedTools`
- **Permission modes**: `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan`
- **Skills preloading** via `skills` frontmatter
- **Hooks** for conditional rules (`PreToolUse`)
- **Model selection**: `sonnet`, `opus`, `haiku`, `inherit`
- **Context isolation**: Subagents have separate context windows
- **Auto-compaction**: Automatic summarization when context fills

---

## Part 3: New Webhook Routes for Container & Subagent Management

### 3.1 Proposed Webhook API Endpoints

```
/api/v2/
├── subagents/
│   ├── POST   /spawn              # Spawn new subagent
│   ├── GET    /                   # List active subagents
│   ├── GET    /{id}               # Get subagent status
│   ├── POST   /{id}/stop          # Stop subagent
│   ├── POST   /{id}/resume        # Resume subagent
│   └── DELETE /{id}               # Terminate subagent
│
├── container/
│   ├── GET    /status             # Container health/resources
│   ├── POST   /exec               # Execute command in container
│   ├── GET    /processes          # List running processes
│   ├── POST   /processes/{pid}/kill  # Kill process
│   ├── GET    /logs               # Get container logs
│   ├── POST   /restart            # Restart container services
│   └── GET    /resources          # CPU/Memory/Disk usage
│
├── agents/
│   ├── POST   /                   # Create new agent definition
│   ├── GET    /                   # List all agents
│   ├── GET    /{name}             # Get agent config
│   ├── PUT    /{name}             # Update agent
│   ├── DELETE /{name}             # Delete agent
│   └── POST   /{name}/validate    # Validate agent config
│
├── skills/
│   ├── POST   /                   # Create new skill
│   ├── GET    /                   # List all skills
│   ├── GET    /{name}             # Get skill details
│   ├── PUT    /{name}             # Update skill
│   ├── DELETE /{name}             # Delete skill
│   └── POST   /{name}/execute     # Execute skill directly
│
└── webhooks/
    ├── POST   /                   # Create webhook config
    ├── GET    /                   # List webhooks
    ├── PUT    /{id}               # Update webhook
    ├── DELETE /{id}               # Delete webhook
    ├── POST   /{id}/commands      # Add command to webhook
    ├── PUT    /{id}/commands/{cmd}# Update command
    ├── DELETE /{id}/commands/{cmd}# Delete command
    └── POST   /{id}/test          # Test webhook
```

### 3.2 Webhook Command Actions (Extended)

Current actions:
- `create_task` - Create task for agent
- `comment` - Post comment back to source
- `ask` - Interactive task with clarification
- `respond` - Direct response
- `forward` - Forward to another service
- `github_reaction` - Add reaction
- `github_label` - Add labels

**New proposed actions:**
- `spawn_subagent` - Spawn specific subagent
- `execute_skill` - Run a skill directly
- `container_exec` - Execute container command
- `chain_tasks` - Create task pipeline
- `parallel_spawn` - Spawn multiple subagents
- `self_improve` - Trigger self-improvement skill

### 3.3 MANDATORY: Immediate Feedback on All Webhooks

**CRITICAL REQUIREMENT:** Every webhook created by Claude Code MUST include immediate user feedback.

#### Why Immediate Feedback Matters
- User knows their request was received (not lost)
- Reduces anxiety about "did it work?"
- Professional UX - all modern bots do this
- Helps debugging (confirms webhook is active)

#### Required Immediate Feedback by Provider

| Provider | Immediate Action | Example |
|----------|------------------|---------|
| **GitHub** | Reaction + Comment | 👀 + "I've received your request..." |
| **Jira** | Comment on ticket | "🤖 Agent is analyzing this ticket..." |
| **Slack** | Reply in thread | "👋 Got it! Working on this now..." |
| **Sentry** | (No direct feedback) | Create Slack/GitHub notification instead |

#### Webhook Creation Checklist (for Claude Code)

When creating ANY webhook, Claude Code MUST:

```markdown
1. ✅ Create the webhook endpoint
2. ✅ Add at least ONE immediate feedback action:
   - GitHub: `github_reaction` (eyes 👀) + `comment`
   - Jira: `comment` action
   - Slack: `respond` in thread
3. ✅ Add the main task action (create_task, ask, etc.)
4. ✅ TEST the webhook with sample payload
5. ✅ Verify immediate feedback was sent
6. ✅ Report webhook URL and test results to user
```

#### Example: Complete Webhook with Immediate Feedback

```python
# When Claude Code creates a GitHub webhook, it MUST include:
webhook_config = {
    "provider": "github",
    "name": "Issue Handler",
    "commands": [
        # FIRST: Immediate feedback (runs instantly)
        {
            "trigger": "issue_comment.created",
            "action": "github_reaction",
            "template": "eyes",  # 👀 reaction
            "priority": 0  # Highest priority - runs first
        },
        {
            "trigger": "issue_comment.created",
            "action": "comment",
            "template": "👋 I've received your request and will analyze it shortly!",
            "priority": 1  # Runs second
        },
        # THEN: Main task (may take time)
        {
            "trigger": "issue_comment.created",
            "action": "create_task",
            "agent": "planning",
            "template": "Analyze: {{comment.body}}",
            "priority": 2  # Runs after feedback
        }
    ]
}
```

#### Testing Webhook Feedback

After creating a webhook, Claude Code MUST test it:

```bash
# Test script that verifies immediate feedback
python scripts/test_webhook.py \
  --webhook-id webhook-123 \
  --event-type "issue_comment.created" \
  --verify-reaction true \
  --verify-comment true \
  --timeout 5  # Feedback must arrive within 5 seconds
```

#### Skill: webhook-feedback-validator

```yaml
name: webhook-feedback-validator
description: Validates that webhooks have proper immediate feedback configured
target: orchestration
```

**Validation checks:**
- [ ] Has at least one immediate feedback action (priority 0 or 1)
- [ ] Feedback action runs before task creation
- [ ] Feedback message is user-friendly
- [ ] Test confirms feedback arrives within 5 seconds

---

## Part 4: Pre-Made Subagents with Skills

### 4.0 Tier 0: Quality & Resilience Subagents (TDD-First)

**Philosophy:** Write tests FIRST, then implement. Verify resilience (עמידות) before deployment.

#### 4.0.1 **TDD Orchestrator Agent**
```yaml
name: tdd-orchestrator
description: Enforces TDD workflow - writes tests first, validates business logic, ensures resilience
tools: Read, Write, Edit, Bash, RunCommand
model: opus  # Complex reasoning for test design
permissionMode: acceptEdits
skills:
  - test-first-writer
  - resilience-tester
  - regression-guard
  - acceptance-validator
  - mutation-tester
```

**Purpose:** Ensures ALL code changes follow TDD and pass resilience checks.

**Workflow:**
```
1. UNDERSTAND requirement/business logic
2. WRITE failing test FIRST (Red)
3. IMPLEMENT minimum code to pass (Green)
4. REFACTOR while keeping tests green
5. ADD resilience tests (edge cases, errors, load)
6. VERIFY acceptance criteria met
7. RUN mutation testing to validate test quality
```

#### Skills for TDD Orchestrator

##### Skill: `test-first-writer`
```markdown
---
name: test-first-writer
description: Writes failing tests BEFORE implementation based on requirements
target: tdd-orchestrator
---

# Test-First Writer

## Purpose
Translates business requirements into failing tests BEFORE any implementation.

## Process
1. Parse requirement/user story
2. Identify acceptance criteria
3. Write test cases that WILL FAIL (no implementation yet)
4. Verify tests fail for the RIGHT reason
5. Document expected behavior in test names

## Test Types to Generate
- Unit tests (isolated logic)
- Integration tests (component interaction)
- Contract tests (API boundaries)
- Acceptance tests (business requirements)

## Output
- Test file with failing tests
- Clear test names describing behavior
- Comments linking to requirements

## Example
Requirement: "User can reset password via email"

Generated tests (all FAIL initially):
- test_password_reset_sends_email_to_valid_user
- test_password_reset_rejects_invalid_email
- test_password_reset_token_expires_after_24h
- test_password_reset_invalidates_old_tokens
- test_password_reset_rate_limits_requests
```

##### Skill: `resilience-tester` (עמידות)
```markdown
---
name: resilience-tester
description: Tests system resilience - error handling, edge cases, load, recovery
target: tdd-orchestrator
---

# Resilience Tester (עמידות)

## Purpose
Ensures code handles failures gracefully and recovers properly.

## Resilience Categories

### 1. Error Handling
- Invalid inputs
- Null/undefined values
- Type mismatches
- Boundary conditions

### 2. Network Resilience
- Timeout handling
- Retry logic
- Circuit breaker patterns
- Partial failures

### 3. Data Resilience
- Database connection failures
- Transaction rollbacks
- Data corruption handling
- Cache invalidation

### 4. Load Resilience
- Concurrent requests
- Memory limits
- Rate limiting
- Queue overflow

### 5. Recovery
- Graceful degradation
- Fallback mechanisms
- State recovery after crash
- Idempotency

## Test Patterns
```python
# Error handling test
def test_handles_database_connection_failure():
    with mock.patch('db.connect', side_effect=ConnectionError):
        result = service.get_user(123)
        assert result.is_error()
        assert "database unavailable" in result.error_message

# Retry test
def test_retries_on_transient_failure():
    mock_api.side_effect = [TimeoutError, TimeoutError, Success]
    result = service.call_external_api()
    assert result.success
    assert mock_api.call_count == 3

# Idempotency test
def test_duplicate_request_is_idempotent():
    result1 = service.create_order(order_id="123", items=[...])
    result2 = service.create_order(order_id="123", items=[...])
    assert result1.order_id == result2.order_id
    assert Order.count() == 1  # Only one order created
```

## Output
- Resilience test suite
- Coverage report for error paths
- Identified weak points
```

##### Skill: `regression-guard`
```markdown
---
name: regression-guard
description: Prevents regressions by ensuring existing tests pass and coverage doesn't drop
target: tdd-orchestrator
---

# Regression Guard

## Purpose
Ensures changes don't break existing functionality.

## Checks
1. All existing tests pass
2. Coverage doesn't decrease
3. No new warnings/errors
4. Performance benchmarks maintained
5. API contracts unchanged (unless intentional)

## Process
```bash
# Before changes
pytest --cov=src --cov-report=json -q > baseline.json

# After changes
pytest --cov=src --cov-report=json -q > current.json

# Compare
python scripts/compare_coverage.py baseline.json current.json
```

## Blocking Conditions
- [ ] Any test failure = BLOCK
- [ ] Coverage drop > 2% = BLOCK
- [ ] New deprecation warnings = WARN
- [ ] Performance regression > 10% = BLOCK
```

##### Skill: `acceptance-validator`
```markdown
---
name: acceptance-validator
description: Validates implementation meets business requirements and acceptance criteria
target: tdd-orchestrator
---

# Acceptance Validator

## Purpose
Ensures implementation actually solves the business problem.

## Process
1. Parse original requirement
2. Extract acceptance criteria
3. Map criteria to test results
4. Generate acceptance report

## Acceptance Report Format
```markdown
# Acceptance Report: [Feature Name]

## Requirement
[Original requirement text]

## Acceptance Criteria Status

| Criteria | Test | Status |
|----------|------|--------|
| User can reset password | test_password_reset_flow | ✅ PASS |
| Email sent within 30s | test_email_delivery_time | ✅ PASS |
| Token expires after 24h | test_token_expiry | ✅ PASS |
| Rate limited to 3/hour | test_rate_limiting | ✅ PASS |

## Overall: ✅ ACCEPTED / ❌ REJECTED

## Notes
[Any observations or concerns]
```
```

##### Skill: `mutation-tester`
```markdown
---
name: mutation-tester
description: Validates test quality by introducing mutations and checking if tests catch them
target: tdd-orchestrator
---

# Mutation Tester

## Purpose
Ensures tests are actually testing the right things (not just passing).

## How It Works
1. Introduce small changes (mutations) to code
2. Run tests
3. If tests still pass = BAD (mutation survived)
4. If tests fail = GOOD (mutation killed)

## Mutation Types
- Change `==` to `!=`
- Change `>` to `>=`
- Remove function calls
- Change return values
- Swap boolean conditions

## Tools
```bash
# Python
pip install mutmut
mutmut run --paths-to-mutate=src/

# JavaScript
npm install stryker-cli
stryker run
```

## Quality Threshold
- Mutation score > 80% = GOOD
- Mutation score < 60% = Tests need improvement
```

---

#### 4.0.2 **End-to-End Validator Agent**
```yaml
name: e2e-validator
description: Validates complete user flows and business scenarios end-to-end
tools: Read, Bash, RunCommand, Playwright
model: sonnet
skills:
  - user-flow-tester
  - scenario-generator
  - visual-regression-checker
```

**Skills:**
- `user-flow-tester` - Tests complete user journeys
- `scenario-generator` - Generates test scenarios from requirements
- `visual-regression-checker` - Catches UI changes via screenshots

---

#### 4.0.3 **TDD Workflow Integration**

**When to Invoke TDD Orchestrator:**

| Trigger | Action |
|---------|--------|
| New feature request | Write acceptance tests first |
| Bug report | Write regression test first |
| Webhook creation | Write integration test first |
| API endpoint | Write contract test first |
| Refactoring | Ensure tests exist before changing |

**Integration with Other Agents:**

```
User Request: "Add password reset feature"
        │
        ▼
┌─────────────────┐
│  PLANNING AGENT │ ──▶ Creates PLAN.md with requirements
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TDD ORCHESTRATOR│ ──▶ Writes failing tests FIRST
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ EXECUTOR AGENT  │ ──▶ Implements until tests pass
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TDD ORCHESTRATOR│ ──▶ Adds resilience tests
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TDD ORCHESTRATOR│ ──▶ Validates acceptance criteria
└────────┬────────┘
         │
         ▼
    ✅ DONE (or loop back if tests fail)
```

---

### 4.1 Tier 1: Core Operational Subagents

#### 4.1.1 **DevOps Agent**
```yaml
name: devops
description: Manages CI/CD, deployments, and infrastructure operations
tools: Read, Grep, Bash, RunCommand
model: sonnet
skills:
  - ci-monitor
  - deployment-manager
  - infrastructure-health
```

**Skills:**
- `ci-monitor` - Monitor CI pipelines, analyze failures
- `deployment-manager` - Trigger/rollback deployments
- `infrastructure-health` - Check service health

#### 4.1.2 **Security Auditor Agent**
```yaml
name: security-auditor
description: Scans code for vulnerabilities, reviews security practices
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit
model: opus
skills:
  - vulnerability-scanner
  - dependency-audit
  - secrets-detector
```

**Skills:**
- `vulnerability-scanner` - SAST/DAST scanning
- `dependency-audit` - Check for vulnerable dependencies
- `secrets-detector` - Find exposed secrets/credentials

### 4.2 Tier 2: External Service Integration Subagents

These agents use **CLI tools + MCP servers + environment variables** to interact with external services.

#### 4.4.0 **Environment & CLI Setup**

All integration agents require proper environment setup in the container:

```bash
# Container environment variables (in .env or docker-compose)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
JIRA_API_TOKEN=xxxxxxxxxxxxxxxx
JIRA_BASE_URL=https://yourcompany.atlassian.net
SENTRY_AUTH_TOKEN=sntrys_xxxxxxxxxxxx
SENTRY_ORG=your-org
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_APP_TOKEN=xapp-xxxxxxxxxxxx
```

**CLI Tools to Install in Dockerfile:**
```dockerfile
# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
RUN apt-get install gh -y

# Jira CLI
RUN go install github.com/ankitpokhrel/jira-cli/cmd/jira@latest

# Sentry CLI
RUN curl -sL https://sentry.io/get-cli/ | bash

# Slack CLI (or use MCP)
RUN npm install -g @slack/cli
```

#### 4.4.1 **GitHub Integration Agent**
```yaml
name: github-integrator
description: Full GitHub operations - repos, issues, PRs, actions, releases via gh CLI and MCP
tools: Read, Write, Bash, RunCommand
model: sonnet
skills:
  - github-issue-manager
  - github-pr-reviewer
  - github-actions-monitor
  - github-release-manager
  - github-repo-analyzer
```

**Skills:**
- `github-issue-manager` - Create, update, close, label issues via `gh issue`
- `github-pr-reviewer` - Review PRs, request changes, approve via `gh pr`
- `github-actions-monitor` - Check workflow runs, re-run failed jobs via `gh run`
- `github-release-manager` - Create releases, manage tags via `gh release`
- `github-repo-analyzer` - Analyze repo stats, contributors, activity

**CLI Commands:**
```bash
gh issue list --state open --label bug
gh pr create --title "Fix: ..." --body "..."
gh pr review 123 --approve
gh run list --workflow ci.yml
gh release create v1.0.0 --notes "Release notes"
gh api repos/{owner}/{repo}/stats/contributors
```

**MCP Integration:**
```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
```

#### 4.4.2 **Jira Integration Agent**
```yaml
name: jira-integrator
description: Full Jira operations - issues, sprints, boards, transitions via jira-cli
tools: Read, Write, Bash, RunCommand
model: sonnet
skills:
  - jira-issue-manager
  - jira-sprint-manager
  - jira-board-analyzer
  - jira-workflow-automator
```

**Skills:**
- `jira-issue-manager` - Create, update, transition issues
- `jira-sprint-manager` - Manage sprints, move issues between sprints
- `jira-board-analyzer` - Analyze board metrics, velocity
- `jira-workflow-automator` - Automate issue transitions

**CLI Commands:**
```bash
jira issue list -q "project=PROJ AND status='In Progress'"
jira issue create -tBug -s"Bug title" -b"Description"
jira issue move PROJ-123 "In Review"
jira sprint list --board 1
jira issue assign PROJ-123 @me
```

**MCP Integration:**
```bash
# Using tom28881/mcp-jira-server
claude mcp add jira -- node /path/to/mcp-jira-server/dist/index.js
```

#### 4.4.3 **Sentry Integration Agent**
```yaml
name: sentry-integrator
description: Error monitoring - analyze errors, releases, performance via sentry-cli and MCP
tools: Read, Bash, RunCommand
disallowedTools: Write, Edit
model: sonnet
skills:
  - sentry-error-analyzer
  - sentry-release-tracker
  - sentry-performance-monitor
  - sentry-alert-manager
```

**Skills:**
- `sentry-error-analyzer` - Analyze error patterns, stack traces, frequency
- `sentry-release-tracker` - Track releases, associate commits with errors
- `sentry-performance-monitor` - Analyze transaction performance
- `sentry-alert-manager` - Check and manage alert rules

**CLI Commands:**
```bash
sentry-cli issues list --project myproject
sentry-cli releases list -o myorg -p myproject
sentry-cli releases new v1.0.0
sentry-cli releases set-commits v1.0.0 --auto
sentry-cli send-event -m "Test event"
```

**MCP Integration:**
```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
```

#### 4.4.4 **Slack Integration Agent**
```yaml
name: slack-integrator
description: Slack operations - messages, channels, threads, notifications via Slack API/MCP
tools: Read, Write, Bash, RunCommand
model: sonnet
skills:
  - slack-messenger
  - slack-channel-manager
  - slack-thread-responder
  - slack-notification-sender
```

**Skills:**
- `slack-messenger` - Send messages to channels/users
- `slack-channel-manager` - Create, archive, manage channels
- `slack-thread-responder` - Reply to threads, manage conversations
- `slack-notification-sender` - Send formatted notifications, alerts

**API/CLI Usage:**
```bash
# Using curl with Slack API
curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel":"C123456","text":"Hello from agent!"}'

# Or using slack-cli npm package
slack chat send --channel general --text "Deployment complete!"
```

#### 4.4.5 **Multi-Service Orchestrator Agent**
```yaml
name: service-orchestrator
description: Coordinates across GitHub, Jira, Sentry, Slack for end-to-end workflows
tools: Read, Write, Bash, RunCommand
model: opus  # Complex cross-service reasoning
skills:
  - cross-service-workflow
  - incident-responder
  - release-coordinator
  - status-aggregator
```

**Skills:**
- `cross-service-workflow` - Coordinate actions across all services
- `incident-responder` - Sentry error → Jira ticket → Slack alert → GitHub PR
- `release-coordinator` - GitHub release → Sentry release → Jira version → Slack announcement
- `status-aggregator` - Aggregate status from all services into single report

**Example Workflow:**
```
1. Sentry detects new error spike
2. Agent creates Jira ticket with error details
3. Agent posts to Slack #incidents channel
4. Agent creates GitHub issue linked to Jira
5. Agent assigns to on-call engineer
```

---

### 4.3 Utility Skills (Not Full Agents)

> **Note:** Git and FileSystem operations don't need dedicated agents. 
> Any agent with `Bash` tool can run git/filesystem commands.
> These are documented as **skills** that can be used by existing agents.

#### Git Operations Skill
```yaml
name: git-operations
description: Git commands for any agent that needs them
target: planning, executor, devops  # Can be used by multiple agents
```

**Common Commands:**
- `git log --oneline --graph` - History
- `git bisect` - Find bug introduction
- `git blame` - Who changed what
- `git diff --stat` - Change analysis

#### FileSystem Operations Skill
```yaml
name: filesystem-operations
description: File system commands for any agent
target: planning, executor, devops
```

**Common Commands:**
- `find` / `fd` - File discovery
- `du -sh` - Disk usage
- `tree` - Structure visualization

---

## Part 4B: Real-Time Background Subagent Logging & Monitoring

### 4B.1 Parallel Subagent Execution Capabilities

Based on Claude Code documentation and testing:

| Feature | Capability |
|---------|------------|
| **Max parallel subagents** | 10 concurrent (queues additional) |
| **Total tasks supported** | 100+ (tested, queued execution) |
| **Context isolation** | Each subagent has own context window |
| **Background mode** | `Ctrl+B` or "run in background" |
| **Auto-deny permissions** | Background agents auto-deny unpermitted actions |

### 4B.2 Real-Time Streaming in Headless Mode

Claude Code CLI supports real-time output streaming:

```bash
# Real-time streaming JSON output
claude -p "Run tests and fix failures" \
  --output-format stream-json \
  --allowedTools "Bash,Read,Edit"
```

**Output format (newline-delimited JSON):**
```json
{"type":"assistant","message":{"content":"Starting test analysis..."}}
{"type":"tool_use","tool":"Bash","input":{"command":"pytest"}}
{"type":"tool_result","output":"...test output..."}
{"type":"assistant","message":{"content":"Found 3 failing tests..."}}
{"type":"result","result":"Fixed all tests","session_id":"abc123"}
```

### 4B.3 Multi-Subagent Real-Time Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PARALLEL SUBAGENT EXECUTION                           │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Subagent 1  │  │ Subagent 2  │  │ Subagent 3  │  │ Subagent N  │    │
│  │ (GitHub)    │  │ (Jira)      │  │ (Sentry)    │  │ (...)       │    │
│  │             │  │             │  │             │  │             │    │
│  │ stream-json │  │ stream-json │  │ stream-json │  │ stream-json │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │                │            │
│         └────────────────┼────────────────┼────────────────┘            │
│                          ▼                                              │
│                 ┌─────────────────┐                                     │
│                 │  LOG AGGREGATOR │                                     │
│                 │                 │                                     │
│                 │ - Multiplexes   │                                     │
│                 │ - Timestamps    │                                     │
│                 │ - Color codes   │                                     │
│                 │ - Filters       │                                     │
│                 └────────┬────────┘                                     │
│                          │                                              │
│         ┌────────────────┼────────────────┐                            │
│         ▼                ▼                ▼                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                    │
│  │  WebSocket  │  │  Log File   │  │  Dashboard  │                    │
│  │  (real-time)│  │  (persist)  │  │  (UI)       │                    │
│  └─────────────┘  └─────────────┘  └─────────────┘                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4B.4 Implementation: Parallel Subagent Runner

```python
# workers/parallel_subagent_runner.py
import asyncio
import json
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class SubagentTask:
    agent_name: str
    prompt: str
    allowed_tools: List[str]

async def run_subagent_with_streaming(
    task: SubagentTask,
    output_callback: callable
) -> Dict:
    """Run a single subagent with real-time output streaming."""
    
    cmd = [
        "claude", "-p", task.prompt,
        "--output-format", "stream-json",
        "--allowedTools", ",".join(task.allowed_tools),
        "--dangerously-skip-permissions"
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Stream output in real-time
    async for line in process.stdout:
        try:
            data = json.loads(line.decode().strip())
            data["agent"] = task.agent_name
            data["timestamp"] = datetime.utcnow().isoformat()
            await output_callback(data)
        except json.JSONDecodeError:
            pass
    
    await process.wait()
    return {"agent": task.agent_name, "exit_code": process.returncode}

async def run_parallel_subagents(
    tasks: List[SubagentTask],
    output_callback: callable,
    max_parallel: int = 10
) -> List[Dict]:
    """Run multiple subagents in parallel with streaming output."""
    
    semaphore = asyncio.Semaphore(max_parallel)
    
    async def run_with_semaphore(task):
        async with semaphore:
            return await run_subagent_with_streaming(task, output_callback)
    
    results = await asyncio.gather(
        *[run_with_semaphore(task) for task in tasks]
    )
    return results
```

### 4B.5 WebSocket Real-Time Log Streaming

```python
# api/subagent_logs.py
from fastapi import WebSocket
from typing import Dict

class SubagentLogHub:
    """WebSocket hub for real-time subagent log streaming."""
    
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
    
    async def broadcast_log(self, task_id: str, log_entry: dict):
        """Broadcast log entry to all connected clients."""
        if task_id in self.connections:
            message = json.dumps({
                "type": "subagent_log",
                "task_id": task_id,
                "agent": log_entry.get("agent"),
                "timestamp": log_entry.get("timestamp"),
                "content": log_entry
            })
            for ws in self.connections[task_id]:
                await ws.send_text(message)

# WebSocket endpoint
@router.websocket("/ws/subagents/{task_id}/logs")
async def subagent_logs_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()
    log_hub.connections.setdefault(task_id, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    finally:
        log_hub.connections[task_id].remove(websocket)
```

### 4B.6 Dashboard Real-Time Log Viewer

```javascript
// Dashboard component for real-time subagent logs
function SubagentLogViewer({ taskId }) {
  const [logs, setLogs] = useState([]);
  const [agents, setAgents] = useState({});
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/subagents/${taskId}/logs`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Group by agent with color coding
      setLogs(prev => [...prev, data]);
      setAgents(prev => ({
        ...prev,
        [data.agent]: {
          status: data.content.type === 'result' ? 'done' : 'running',
          lastUpdate: data.timestamp
        }
      }));
    };
    
    return () => ws.close();
  }, [taskId]);
  
  return (
    <div className="subagent-log-viewer">
      {/* Agent status cards */}
      <div className="agent-status-grid">
        {Object.entries(agents).map(([name, status]) => (
          <AgentStatusCard key={name} name={name} {...status} />
        ))}
      </div>
      
      {/* Real-time log stream */}
      <div className="log-stream">
        {logs.map((log, i) => (
          <LogEntry key={i} {...log} />
        ))}
      </div>
    </div>
  );
}
```

### 4B.7 CLI Command for Parallel Execution with Live Output

```bash
# Run multiple subagents with live multiplexed output
python -m workers.parallel_runner \
  --agents "github-integrator,jira-integrator,sentry-integrator" \
  --prompt "Check status of project X" \
  --output live

# Output (color-coded by agent):
# [github-integrator] 🔍 Checking open PRs...
# [jira-integrator]   📋 Fetching sprint issues...
# [sentry-integrator] 🐛 Analyzing recent errors...
# [github-integrator] ✅ Found 3 open PRs
# [jira-integrator]   ✅ Sprint has 12 issues
# [sentry-integrator] ⚠️  5 new errors in last 24h
```

---

## Part 5: Data Persistence Strategy

> **Note:** Self-Improvement features (Skill Factory, Agent Factory, Pattern Learner) 
> are deferred to **Phase 2**. Focus on core functionality first.

### 6.1 Current Persistence (Verified)

| Data Type | Storage | Location | Persistence |
|-----------|---------|----------|-------------|
| Tasks | SQLite | `/data/db/machine.db` | ✅ Volume |
| Sessions | SQLite | `/data/db/machine.db` | ✅ Volume |
| Webhooks | SQLite | `/data/db/machine.db` | ✅ Volume |
| Events | SQLite | `/data/db/machine.db` | ✅ Volume |
| Conversations | SQLite | `/data/db/machine.db` | ✅ Volume |
| User Agents | Files | `/data/config/agents/` | ✅ Volume |
| User Skills | Files | `/data/config/skills/` | ✅ Volume |
| Credentials | JSON | `/data/credentials/` | ✅ Volume |
| Registry | YAML | `/data/registry/` | ✅ Volume |

### 6.2 Enhanced Persistence Requirements

#### New Database Models Needed

```python
# Subagent execution tracking
class SubagentExecutionDB(Base):
    __tablename__ = "subagent_executions"
    
    execution_id = Column(String(255), primary_key=True)
    parent_task_id = Column(String(255), ForeignKey("tasks.task_id"))
    agent_name = Column(String(255), nullable=False)
    mode = Column(String(50))  # foreground, background, parallel
    status = Column(String(50))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    context_tokens = Column(Integer)
    result_summary = Column(Text)

# Skill execution tracking
class SkillExecutionDB(Base):
    __tablename__ = "skill_executions"
    
    execution_id = Column(String(255), primary_key=True)
    task_id = Column(String(255), ForeignKey("tasks.task_id"))
    skill_name = Column(String(255), nullable=False)
    input_params = Column(Text)  # JSON
    output_result = Column(Text)  # JSON
    success = Column(Boolean)
    executed_at = Column(DateTime)

```

### 6.3 Redis Enhancement for Real-time State

```python
# New Redis keys for subagent management
class RedisKeys:
    # Active subagents
    ACTIVE_SUBAGENTS = "subagents:active"  # Set of active subagent IDs
    SUBAGENT_STATUS = "subagent:{id}:status"  # Hash with status details
    SUBAGENT_CONTEXT = "subagent:{id}:context"  # Context window state
    
    # Parallel execution tracking
    PARALLEL_GROUP = "parallel:{group_id}:agents"  # Set of agents in group
    PARALLEL_RESULTS = "parallel:{group_id}:results"  # Hash of results
    
    # Container state
    CONTAINER_PROCESSES = "container:processes"  # Hash of running processes
    CONTAINER_RESOURCES = "container:resources"  # Hash of resource usage
    
    # Skill execution queue
    SKILL_QUEUE = "skills:queue"  # List of pending skill executions
```

---

## Part 7: Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Deliverables:**
1. New database models for subagent/skill tracking
2. Enhanced Redis client for real-time state
3. Basic container management API endpoints
4. Subagent spawn/stop API endpoints

**Files to Create/Modify:**
- `core/database/models.py` - Add new models
- `core/database/redis_client.py` - Add subagent tracking
- `api/subagents.py` - New subagent management API
- `api/container.py` - New container management API

### Phase 2: Subagent Orchestration (Week 3-4)

**Deliverables:**
1. Parallel subagent execution support
2. Subagent context management
3. Background task handling
4. Result aggregation

**Files to Create/Modify:**
- `workers/subagent_worker.py` - Subagent execution worker
- `core/subagent_orchestrator.py` - Orchestration logic
- `core/context_manager.py` - Context window management

### Phase 3: Service Integrations (Week 5-6)

**Deliverables:**
1. GitHub Integration Agent with CLI
2. Jira Integration Agent with CLI
3. Slack notifications

**Files to Create:**
- `.claude/agents/github-integrator.md`
- `.claude/agents/jira-integrator.md`
- `skills/slack-notifier/SKILL.md`

### Phase 4: TDD & Testing (Week 7-8)

**Deliverables:**
1. TDD Orchestrator Agent
2. Test-first-writer skill
3. Resilience-tester skill

**Files to Create:**
- `.claude/agents/tdd-orchestrator.md`
- `skills/test-first-writer/SKILL.md`
- `skills/resilience-tester/SKILL.md`

---

> **Phase 5+ (Future):** Self-improvement features, additional integrations

---

## Part 6: Security Considerations

### 6.1 Permission Model

```yaml
# Permission levels
permissions:
  webhook_creation:
    requires: user_approval
    secret_management: encrypted
    
  agent_creation:
    requires: brain_approval
    validation: mandatory
    tool_restrictions: enforced
    
  webhook_creation:
    requires: user_approval
    secret_management: encrypted
    
  container_exec:
    requires: explicit_allowlist
    audit_logging: mandatory
    sandboxed: true
```

### 6.2 Validation Requirements

1. **Webhook Validation:**
   - Endpoint reachability
   - Secret strength verification
   - Command action validation
   - Immediate feedback configured

2. **Agent Validation:**
   - Frontmatter schema validation
   - Tool permission verification

### 6.3 Audit Trail

All actions logged to:
- `TaskDB` - Which task triggered it
- `WebhookEventDB` - If webhook-triggered
- Container logs - Execution details

---

## Part 7: Example Workflows

### 7.1 Parallel Research Workflow

```
User: "Research the authentication, database, and API modules in parallel"

Brain Agent:
1. Analyzes request → needs parallel subagents
2. Spawns 3 background Planning agents (parallel)
3. Aggregates results
4. Returns consolidated report
```

### 7.2 Webhook-Triggered Task Chain

```
GitHub Issue Created → Webhook Received

Webhook Engine:
1. Immediate feedback: 👀 reaction + comment
2. Matches trigger: issues.opened
3. Creates task for Planning agent
4. Planning analyzes → creates PLAN.md
5. If simple: Executor implements fix
6. Posts result back to GitHub
```

---

## Part 8: Multi-Account & Machine Management

### 8.1 Account Registration on Credential Upload

When a user uploads a new `claude.json` credential file, the system should automatically register/update the account.

#### Database Model

```python
class AccountDB(Base):
    """User account database model."""
    __tablename__ = "accounts"
    
    account_id = Column(String(255), primary_key=True)  # From credential user_id
    email = Column(String(255), nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    credential_status = Column(String(50), default="valid")  # valid, expired, revoked
    credential_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(Text, default="{}")
    
    # Relationships
    machines = relationship("MachineDB", back_populates="account")
    sessions = relationship("SessionDB", back_populates="account")
```

#### Enhanced Credential Upload Flow

```python
@router.post("/credentials/upload")
async def upload_credentials(file: UploadFile, db: AsyncSession):
    # 1. Validate credential JSON
    creds = ClaudeCredentials(**json.loads(content))
    
    # 2. Create or update account
    account = await db.execute(
        select(AccountDB).where(AccountDB.account_id == creds.user_id)
    )
    existing = account.scalar_one_or_none()
    
    if existing:
        existing.credential_expires_at = creds.expires_at_datetime
        existing.credential_status = "valid"
        existing.updated_at = datetime.utcnow()
    else:
        new_account = AccountDB(
            account_id=creds.user_id,
            email=creds.email,
            credential_expires_at=creds.expires_at_datetime,
        )
        db.add(new_account)
    
    # 3. Save credential file
    creds_path.write_bytes(content)
    
    # 4. Return account info
    return {"account_id": creds.user_id, "registered": not existing}
```

### 8.2 Machine-to-Account Linking

Each running container/machine instance is linked to an account.

#### Database Model

```python
class MachineDB(Base):
    """Machine/container instance database model."""
    __tablename__ = "machines"
    
    machine_id = Column(String(255), primary_key=True)  # e.g., "claude-agent-001"
    account_id = Column(String(255), ForeignKey("accounts.account_id"), nullable=True)
    display_name = Column(String(255), nullable=True)
    status = Column(String(50), default="offline")  # online, offline, busy, error
    last_heartbeat = Column(DateTime, nullable=True)
    container_id = Column(String(255), nullable=True)  # Docker container ID
    host_info = Column(Text, default="{}")  # JSON: hostname, IP, resources
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("AccountDB", back_populates="machines")
```

#### Redis Keys for Real-time Machine Status

```python
class RedisKeys:
    # Machine management
    MACHINE_STATUS = "machine:{id}:status"      # Hash: status, last_heartbeat
    MACHINE_METRICS = "machine:{id}:metrics"    # Hash: cpu, memory, tasks_running
    ACTIVE_MACHINES = "machines:active"         # Set of online machine IDs
    MACHINE_ACCOUNT = "machine:{id}:account"    # String: linked account_id
```

#### Machine Registration API

```python
@router.post("/machines/register")
async def register_machine(
    machine_id: str,
    account_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Register a new machine or update existing."""
    machine = MachineDB(
        machine_id=machine_id,
        account_id=account_id,
        status="online",
        last_heartbeat=datetime.utcnow()
    )
    await db.merge(machine)
    await redis_client.sadd(RedisKeys.ACTIVE_MACHINES, machine_id)
    await redis_client.hset(f"machine:{machine_id}:status", {
        "status": "online",
        "heartbeat": datetime.utcnow().isoformat()
    })
    return {"machine_id": machine_id, "status": "registered"}

@router.post("/machines/{machine_id}/heartbeat")
async def machine_heartbeat(machine_id: str):
    """Update machine heartbeat (called every 30s)."""
    await redis_client.hset(f"machine:{machine_id}:status", {
        "heartbeat": datetime.utcnow().isoformat()
    })
    return {"ok": True}
```

### 8.3 Dashboard UI Support

#### 8.3.1 Account Switcher Component

**Location:** Top-right corner (replacing static machine ID)

```tsx
// components/AccountSwitcher.tsx
interface Account {
  account_id: string;
  email: string;
  display_name?: string;
  credential_status: "valid" | "expired" | "expiring_soon";
  machines: Machine[];
}

interface Machine {
  machine_id: string;
  status: "online" | "offline" | "busy";
  display_name?: string;
}

export function AccountSwitcher() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [activeAccount, setActiveAccount] = useState<Account | null>(null);
  const [activeMachine, setActiveMachine] = useState<Machine | null>(null);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger>
        <div className="flex items-center gap-2">
          <StatusDot status={activeMachine?.status} />
          <span>{activeMachine?.machine_id || "No Machine"}</span>
          <ChevronDown className="h-4 w-4" />
        </div>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end">
        {/* Account Section */}
        <DropdownMenuLabel>Account</DropdownMenuLabel>
        {accounts.map(account => (
          <DropdownMenuItem 
            key={account.account_id}
            onClick={() => switchAccount(account)}
          >
            <User className="mr-2 h-4 w-4" />
            {account.email || account.account_id}
            {account.credential_status === "expiring_soon" && (
              <Badge variant="warning">Expiring</Badge>
            )}
          </DropdownMenuItem>
        ))}
        
        <DropdownMenuSeparator />
        
        {/* Machine Section */}
        <DropdownMenuLabel>Machines</DropdownMenuLabel>
        {activeAccount?.machines.map(machine => (
          <DropdownMenuItem
            key={machine.machine_id}
            onClick={() => switchMachine(machine)}
          >
            <StatusDot status={machine.status} className="mr-2" />
            {machine.display_name || machine.machine_id}
          </DropdownMenuItem>
        ))}
        
        <DropdownMenuSeparator />
        
        {/* Actions */}
        <DropdownMenuItem onClick={openCredentialUpload}>
          <Upload className="mr-2 h-4 w-4" />
          Upload New Credentials
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

#### 8.3.2 Account Management Page

**Route:** `/settings/accounts`

```tsx
// pages/settings/accounts.tsx
export function AccountsPage() {
  return (
    <div className="space-y-6">
      <h1>Account Management</h1>
      
      {/* Registered Accounts */}
      <Card>
        <CardHeader>
          <CardTitle>Registered Accounts</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Machines</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.map(account => (
                <TableRow key={account.account_id}>
                  <TableCell>{account.email}</TableCell>
                  <TableCell>
                    <CredentialStatusBadge status={account.credential_status} />
                  </TableCell>
                  <TableCell>{formatDate(account.credential_expires_at)}</TableCell>
                  <TableCell>{account.machines.length} machines</TableCell>
                  <TableCell>
                    <Button variant="ghost" onClick={() => refreshCredentials(account)}>
                      Refresh
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      
      {/* Upload New Credentials */}
      <Card>
        <CardHeader>
          <CardTitle>Add New Account</CardTitle>
        </CardHeader>
        <CardContent>
          <CredentialUploadDropzone onUpload={handleUpload} />
        </CardContent>
      </Card>
    </div>
  );
}
```

#### 8.3.3 Machine Status Panel

**Location:** Sidebar or Overview page

```tsx
// components/MachineStatusPanel.tsx
export function MachineStatusPanel() {
  const { machines } = useMachines();
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Server className="h-5 w-5" />
          Machines
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {machines.map(machine => (
          <div 
            key={machine.machine_id}
            className="flex items-center justify-between p-2 rounded border"
          >
            <div className="flex items-center gap-2">
              <StatusDot status={machine.status} />
              <span className="font-mono text-sm">{machine.machine_id}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {machine.status === "busy" && (
                <Badge variant="secondary">
                  {machine.active_tasks} tasks
                </Badge>
              )}
              <span>
                {machine.status === "online" 
                  ? `${machine.cpu_usage}% CPU` 
                  : "Offline"}
              </span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

#### 8.3.4 Real-time Status Updates via WebSocket

```typescript
// hooks/useMachineStatus.ts
export function useMachineStatus() {
  const [machines, setMachines] = useState<Machine[]>([]);
  
  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/machines/status`);
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      setMachines(prev => 
        prev.map(m => 
          m.machine_id === update.machine_id 
            ? { ...m, ...update } 
            : m
        )
      );
    };
    
    return () => ws.close();
  }, []);
  
  return { machines };
}
```

### 8.4 API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/credentials/upload` | POST | Upload credentials & register account |
| `/accounts` | GET | List all registered accounts |
| `/accounts/{id}` | GET | Get account details with machines |
| `/accounts/{id}` | DELETE | Remove account |
| `/machines` | GET | List all machines |
| `/machines/register` | POST | Register new machine |
| `/machines/{id}/heartbeat` | POST | Update machine heartbeat |
| `/machines/{id}/link` | POST | Link machine to account |
| `/ws/machines/status` | WS | Real-time machine status stream |

### 8.5 Implementation Files

**Backend:**
- `core/database/models.py` - Add `AccountDB`, `MachineDB` models
- `api/credentials.py` - Enhance upload to register accounts
- `api/accounts.py` - New account management API
- `api/machines.py` - New machine management API
- `core/database/redis_client.py` - Add machine status tracking

**Frontend (dashboard-v2):**
- `src/components/AccountSwitcher.tsx` - Account/machine dropdown
- `src/components/MachineStatusPanel.tsx` - Machine status display
- `src/pages/settings/accounts.tsx` - Account management page
- `src/hooks/useMachineStatus.ts` - Real-time machine updates
- `src/hooks/useAccounts.ts` - Account data fetching

### 8.6 TDD Requirements

> See [TDD-REQUIREMENTS.md](./TDD-REQUIREMENTS.md) for complete business-level tests for Part 8.

---

## Part 9: Session Status & Cost Tracking

### 9.1 Cost Calculation

#### How Costs Are Calculated

Costs come from the Claude CLI output after each task execution:

```python
# Claude CLI returns JSON with cost data:
{
    "type": "result",
    "total_cost_usd": 0.0234,
    "usage": {
        "input_tokens": 1500,
        "output_tokens": 800
    }
}
```

#### Pricing Model (as of 2024)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude 3 Opus | $15.00 | $75.00 |

#### Cost Formula

```python
cost_usd = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
```

#### Storage

```python
# TaskDB - per-task cost
cost_usd = Column(Float, default=0.0)
input_tokens = Column(Integer, default=0)
output_tokens = Column(Integer, default=0)

# SessionDB - aggregated cost
total_cost_usd = Column(Float, default=0.0)
total_tasks = Column(Integer, default=0)
```

### 9.2 Session Status Display

#### Current Session Card

The dashboard should display a session status card with:

```tsx
// components/SessionStatusCard.tsx
interface SessionStatus {
  session_id: string;
  status: "active" | "idle" | "disconnected";
  running_tasks: number;
  total_cost_usd: number;
  total_tasks: number;
  started_at: string;
  last_activity: string;
  duration_seconds: number;
}

export function SessionStatusCard() {
  const { session } = useCurrentSession();
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <StatusDot status={session.status} />
            Current Session
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={resetSession}>
            <RotateCcw className="h-4 w-4 mr-1" />
            Reset
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <Stat label="Status" value={session.status} />
          <Stat label="Running Tasks" value={session.running_tasks} />
          <Stat label="Total Cost" value={`$${session.total_cost_usd.toFixed(4)}`} />
          <Stat label="Duration" value={formatDuration(session.duration_seconds)} />
        </div>
      </CardContent>
    </Card>
  );
}
```

#### Status Indicators

| Status | Color | Meaning |
|--------|-------|---------|
| `active` | 🟢 Green | Tasks currently running |
| `idle` | 🟡 Yellow | Connected but no active tasks |
| `disconnected` | ⚫ Gray | Session ended |
| `error` | 🔴 Red | Error state |

### 9.3 Session Reset

#### What Reset Does

1. **Clears** conversation context (messages)
2. **Preserves** cost history and task records
3. **Resets** running task count to 0
4. **Updates** `last_reset_at` timestamp

#### API Endpoint

```python
@router.post("/sessions/{session_id}/reset")
async def reset_session(session_id: str, db: AsyncSession):
    """Reset session context while preserving history."""
    
    # Clear conversation context
    await db.execute(
        delete(ConversationMessageDB)
        .where(ConversationMessageDB.conversation_id.in_(
            select(ConversationDB.conversation_id)
            .where(ConversationDB.session_id == session_id)
        ))
    )
    
    # Update session
    session = await db.get(SessionDB, session_id)
    session.last_reset_at = datetime.utcnow()
    session.context_cleared = True
    
    await db.commit()
    
    return {"success": True, "reset_at": session.last_reset_at.isoformat()}
```

### 9.4 Weekly Session Summary

#### Dashboard Display

```tsx
// components/WeeklySessionSummary.tsx
interface WeeklySummary {
  total_cost_usd: number;
  total_tasks: number;
  active_days: number;
  sessions: number;
  daily: DailyStat[];
}

interface DailyStat {
  date: string;
  cost_usd: number;
  task_count: number;
  sessions: number;
}

export function WeeklySessionSummary() {
  const { summary } = useWeeklySummary();
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>This Week</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <Stat label="Total Cost" value={`$${summary.total_cost_usd.toFixed(2)}`} />
          <Stat label="Tasks" value={summary.total_tasks} />
          <Stat label="Sessions" value={summary.sessions} />
          <Stat label="Active Days" value={`${summary.active_days}/7`} />
        </div>
        
        {/* Daily Chart */}
        <WeeklyCostChart data={summary.daily} />
      </CardContent>
    </Card>
  );
}
```

#### Weekly Cost Chart

```tsx
// components/WeeklyCostChart.tsx
export function WeeklyCostChart({ data }: { data: DailyStat[] }) {
  const chartData = {
    labels: data.map(d => formatDate(d.date, "EEE")), // Mon, Tue, etc.
    datasets: [
      {
        label: "Cost ($)",
        data: data.map(d => d.cost_usd),
        borderColor: "rgb(34, 197, 94)",
        backgroundColor: "rgba(34, 197, 94, 0.1)",
        fill: true,
      },
      {
        label: "Tasks",
        data: data.map(d => d.task_count),
        borderColor: "rgb(59, 130, 246)",
        yAxisID: "y1",
      }
    ]
  };
  
  return <Line data={chartData} options={chartOptions} />;
}
```

### 9.5 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions/{id}/status` | GET | Get current session status |
| `/sessions/{id}/reset` | POST | Reset session context |
| `/sessions/summary/weekly` | GET | Get weekly summary |
| `/dashboard/session/current` | GET | Get current session for dashboard |
| `/dashboard/sessions/history` | GET | Get session history (7 days) |
| `/analytics/costs/daily` | GET | Daily cost breakdown |
| `/analytics/summary` | GET | Today's and total costs |

### 9.6 Implementation Files

**Backend:**
- `api/sessions.py` - Session status and reset endpoints
- `api/analytics.py` - Already exists, add weekly summary
- `api/dashboard.py` - Add session display endpoints

**Frontend (dashboard-v2):**
- `src/components/SessionStatusCard.tsx` - Current session display
- `src/components/WeeklySessionSummary.tsx` - Weekly summary
- `src/components/WeeklyCostChart.tsx` - Cost chart
- `src/hooks/useCurrentSession.ts` - Session data hook
- `src/hooks/useWeeklySummary.ts` - Weekly data hook

### 9.7 TDD Requirements

> See [TDD-REQUIREMENTS.md](./TDD-REQUIREMENTS.md) Part 9 for complete business-level tests.

---

## Summary

This plan provides architecture for:

✅ **Multi-subagent management** - Foreground, background, and parallel (up to 10)
✅ **Container control** - API endpoints for process/resource management  
✅ **Data persistence** - All state persisted to SQLite/Redis
✅ **Webhook orchestration** - Immediate feedback + task creation
✅ **TDD enforcement** - Test-first workflow with resilience testing
✅ **Service integrations** - GitHub, Jira, Sentry, Slack via CLI + MCP
✅ **Real-time logging** - Stream subagent output via WebSocket
✅ **Multi-account management** - Account registration on credential upload, machine linking
✅ **Dashboard UI** - Account switcher, machine status panel, settings page
✅ **Session status & cost tracking** - Real-time session display, weekly summaries, cost calculation
✅ **TDD coverage** - Business-level tests for all requirements (see [TDD-REQUIREMENTS.md](./TDD-REQUIREMENTS.md))

**Deferred to Phase 2:** Self-improvement (Skill Factory, Agent Factory, Pattern Learner)
