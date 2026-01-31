# Business Logic Testing Guide for Agent-Bot

> Comprehensive testing strategy for verifying business logic and requirements across all agent-bot services

## Overview

This document defines the testing strategy for agent-bot, focusing on **business logic and requirements** rather than implementation details. Tests verify **behavior and outcomes** - what the system does, not how it does it internally.

**Testing Philosophy:**
- Test WHAT the system does, not HOW it does it
- Verify business rules and invariants
- Test edge cases and error boundaries
- No mocking internal implementation - only external dependencies

---

## Test Structure

```
agent-bot/
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── factories/               # Test data factories
│   │   ├── task_factory.py
│   │   ├── session_factory.py
│   │   ├── webhook_factory.py
│   │   └── conversation_factory.py
│   └── fixtures/                # Static test data
│       ├── github_payloads.py
│       ├── jira_payloads.py
│       ├── slack_payloads.py
│       └── sentry_payloads.py
│
├── agent-engine/tests/          # Core execution engine
├── api-gateway/tests/           # Webhook processing
├── dashboard-api/tests/         # Analytics & monitoring
├── task-logger/tests/           # Structured task logging
├── api-services/tests/          # External API wrappers
├── mcp-servers/tests/           # MCP protocol servers
└── oauth-service/tests/         # Authentication (exists)
```

---

## 1. Agent Engine Tests

Location: `agent-engine/tests/`

### 1.1 Task Lifecycle Business Logic

**File:** `test_task_lifecycle.py`

Tests the task state machine that governs all agent executions.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_task_created_in_queued_status` | New tasks start as QUEUED | Assert status == QUEUED |
| `test_task_transitions_to_running_when_picked_up` | Processing starts transitions to RUNNING | Assert status == RUNNING, started_at is set |
| `test_task_cannot_transition_from_completed` | Completed tasks are final | Assert transition raises error |
| `test_task_cannot_transition_from_failed` | Failed tasks are final | Assert transition raises error |
| `test_task_cannot_transition_from_cancelled` | Cancelled tasks are final | Assert transition raises error |
| `test_running_task_can_wait_for_input` | Long tasks may need user input | Assert RUNNING → WAITING_INPUT allowed |
| `test_waiting_task_can_resume` | Input received resumes execution | Assert WAITING_INPUT → RUNNING allowed |
| `test_task_duration_calculated_on_completion` | Duration tracked for analytics | Assert duration_seconds > 0 when completed |
| `test_task_cost_accumulated_correctly` | Cost tracking for billing | Assert cost_usd matches token calculation |
| `test_task_requires_input_message` | Tasks must have work to do | Assert validation error on empty input |

**State Machine Diagram:**
```
QUEUED ──────────────────┬─────────────────────────────> CANCELLED
   │                     │
   v                     │
RUNNING ─────────────────┼─────────────────────────────> CANCELLED
   │                     │                      │
   ├───> WAITING_INPUT ──┼──────────────────────┤
   │          │          │                      │
   │          └──────────┤                      │
   │                     │                      │
   ├─────────────────────┼──────────────────────┼─────> COMPLETED
   │                     │                      │
   └─────────────────────┴──────────────────────┴─────> FAILED
```

**Behavior Test Example:**
```python
async def test_complete_task_flow():
    """Business requirement: Tasks flow from QUEUED → RUNNING → COMPLETED"""
    task = create_task(input_message="Fix authentication bug")

    assert task.status == TaskStatus.QUEUED
    assert task.started_at is None

    task.start()
    assert task.status == TaskStatus.RUNNING
    assert task.started_at is not None

    task.complete(result="Bug fixed", cost_usd=0.05)
    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at is not None
    assert task.duration_seconds > 0
    assert task.cost_usd == 0.05
```

### 1.2 Session Management Business Logic

**File:** `test_session_management.py`

Tests per-user session tracking and cost aggregation.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_session_aggregates_task_costs` | Per-user cost tracking | Assert session.total_cost_usd == sum(task costs) |
| `test_session_tracks_task_count` | Usage metrics | Assert session.total_tasks increments |
| `test_session_becomes_inactive_on_rate_limit` | Rate limiting protection | Assert session.active == False when limited |
| `test_session_requires_user_and_machine` | Valid session needs identity | Assert validation error without user_id/machine_id |
| `test_disconnected_session_preserves_data` | Historical data retention | Assert costs/tasks preserved after disconnect |

**Behavior Test Example:**
```python
async def test_session_cost_accumulation():
    """Business requirement: Session tracks cumulative costs"""
    session = create_session(user_id="user-1", machine_id="machine-1")

    assert session.total_cost_usd == 0
    assert session.total_tasks == 0

    task1 = create_task(session_id=session.session_id)
    task1.complete(cost_usd=0.10)
    session.add_completed_task(task1)

    assert session.total_cost_usd == 0.10
    assert session.total_tasks == 1

    task2 = create_task(session_id=session.session_id)
    task2.complete(cost_usd=0.25)
    session.add_completed_task(task2)

    assert session.total_cost_usd == 0.35
    assert session.total_tasks == 2
```

### 1.3 CLI Provider Selection Business Logic

**File:** `test_cli_provider_selection.py`

Tests how agent types map to CLI providers and models.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_complex_agents_use_opus_model` | Quality over speed for planning | Assert model == "opus" for planning/brain agents |
| `test_execution_agents_use_sonnet_model` | Speed for implementation | Assert model == "sonnet" for executor agent |
| `test_provider_selection_from_environment` | Configurable provider | Assert CLI_PROVIDER env var respected |
| `test_unknown_provider_raises_error` | Fail-fast on misconfiguration | Assert error for invalid provider |

**Agent-to-Model Mapping:**
```python
COMPLEX_AGENTS = ["planning", "consultation", "question_asking", "brain"]
# → Uses Opus (Claude) or Pro model (Cursor)

EXECUTION_AGENTS = ["executor", "github-issue-handler", "jira-code-plan"]
# → Uses Sonnet (Claude) or Standard model (Cursor)
```

**Behavior Test Example:**
```python
async def test_agent_type_determines_model():
    """Business requirement: Complex tasks get best model"""
    COMPLEX_AGENTS = ["planning", "consultation", "question_asking", "brain"]
    EXECUTION_AGENTS = ["executor", "github-issue-handler", "jira-code-plan"]

    for agent in COMPLEX_AGENTS:
        model = get_model_for_agent(agent)
        assert model in ["opus", "claude-opus-4"], f"{agent} should use Opus"

    for agent in EXECUTION_AGENTS:
        model = get_model_for_agent(agent)
        assert model in ["sonnet", "claude-sonnet-4"], f"{agent} should use Sonnet"
```

### 1.4 Task Routing Business Logic

**File:** `test_task_routing.py`

Tests routing of tasks to specialized agents based on source.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_github_issue_routes_to_issue_handler` | Issue handling specialized | Assert agent == "github-issue-handler" |
| `test_github_pr_routes_to_pr_review` | PR review specialized | Assert agent == "github-pr-review" |
| `test_jira_ticket_routes_to_code_plan` | Jira integration | Assert agent == "jira-code-plan" |
| `test_slack_message_routes_to_inquiry` | Slack Q&A | Assert agent == "slack-inquiry" |
| `test_sentry_alert_routes_to_error_handler` | Error triage | Assert agent == "sentry-error-handler" |
| `test_discovery_task_routes_to_planning` | Code discovery | Assert agent == "planning" |

**Routing Table:**
| Source | Event Type | Target Agent |
|--------|------------|--------------|
| GitHub | Issue opened/commented | github-issue-handler |
| GitHub | PR opened/reviewed | github-pr-review |
| Jira | Issue with AI-Fix label | jira-code-plan |
| Slack | @agent mention | slack-inquiry |
| Sentry | Error alert | sentry-error-handler |
| Dashboard | Discovery request | planning |
| Dashboard | Implementation request | executor |

---

## 2. API Gateway Tests

Location: `api-gateway/tests/`

### 2.1 GitHub Webhook Business Logic

**File:** `test_github_webhooks.py`

Tests processing of GitHub webhook events.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_issue_opened_creates_task` | New issues trigger agents | Assert task created with issue data |
| `test_issue_edited_creates_task` | Edited issues may need attention | Assert task created |
| `test_issue_labeled_with_ai_fix_creates_task` | AI-Fix label triggers automation | Assert task created |
| `test_issue_comment_created_creates_task` | Comments may need response | Assert task created |
| `test_pr_opened_creates_task` | New PRs need review | Assert task created |
| `test_pr_synchronize_updates_task` | Code push updates review context | Assert existing task updated or new created |
| `test_pr_review_created_creates_task` | Review feedback needs processing | Assert task created |
| `test_invalid_signature_rejected` | Security requirement | Assert 401 returned |
| `test_unsupported_event_ignored` | Only relevant events processed | Assert 200 with "ignored" message |
| `test_bot_comments_ignored` | Prevent infinite loops | Assert no task for bot comments |

**Supported GitHub Events:**
- `issues`: opened, edited, labeled
- `issue_comment`: created
- `pull_request`: opened, synchronize, reopened
- `pull_request_review`: submitted

**Behavior Test Example:**
```python
async def test_github_issue_to_task_flow():
    """Business requirement: GitHub issues become agent tasks"""
    payload = github_issue_opened_payload(
        repo="myorg/myrepo",
        issue_number=123,
        title="Authentication fails for SSO users",
        body="When logging in via SSO, users see a 500 error..."
    )

    response = await webhook_handler.handle_github(payload, signature=valid_signature)

    assert response.status_code == 202
    task = await get_task(response.task_id)
    assert task.source == "webhook"
    assert task.source_metadata["provider"] == "github"
    assert task.source_metadata["repo"] == "myorg/myrepo"
    assert task.source_metadata["issue_number"] == 123
    assert "Authentication fails" in task.input_message
```

### 2.2 Jira Webhook Business Logic

**File:** `test_jira_webhooks.py`

Tests processing of Jira webhook events with AI-Fix label filtering.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_issue_created_with_ai_fix_label_creates_task` | AI-Fix label required | Assert task created |
| `test_issue_created_without_ai_fix_ignored` | Only AI-Fix processed | Assert no task created |
| `test_issue_updated_with_ai_fix_label_creates_task` | Label added later works | Assert task created |
| `test_comment_created_on_ai_fix_issue_creates_task` | Comments extend conversation | Assert task created |
| `test_invalid_signature_rejected` | Security requirement | Assert 401 returned |
| `test_task_contains_jira_metadata` | Context preserved | Assert issue_key, project, summary in metadata |

**Supported Jira Events:**
- `jira:issue_created` (with AI-Fix label)
- `jira:issue_updated` (with AI-Fix label)
- `comment_created` (on AI-Fix issues)

**Behavior Test Example:**
```python
async def test_jira_ai_fix_label_requirement():
    """Business requirement: Only AI-Fix labeled tickets processed"""
    # Without AI-Fix label - should be ignored
    payload_no_label = jira_issue_created_payload(
        issue_key="PROJ-123",
        labels=["bug", "urgent"]
    )
    response = await webhook_handler.handle_jira(payload_no_label, signature=valid_signature)
    assert response.status_code == 200
    assert response.body["action"] == "ignored"

    # With AI-Fix label - should create task
    payload_with_label = jira_issue_created_payload(
        issue_key="PROJ-123",
        labels=["bug", "AI-Fix"]
    )
    response = await webhook_handler.handle_jira(payload_with_label, signature=valid_signature)
    assert response.status_code == 202
    assert response.task_id is not None
```

### 2.3 Slack Webhook Business Logic

**File:** `test_slack_webhooks.py`

Tests processing of Slack events.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_app_mention_creates_task` | @agent mentions trigger | Assert task created |
| `test_direct_message_creates_task` | DM to bot works | Assert task created |
| `test_message_in_non_subscribed_channel_ignored` | Channel filtering | Assert no task |
| `test_bot_own_message_ignored` | Prevent self-response loops | Assert no task |
| `test_task_contains_slack_context` | Reply context preserved | Assert channel, thread_ts, user in metadata |

### 2.4 Sentry Webhook Business Logic

**File:** `test_sentry_webhooks.py`

Tests processing of Sentry error alerts.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_new_error_creates_task` | Errors trigger investigation | Assert task created |
| `test_regression_creates_high_priority_task` | Regressions urgent | Assert priority == "high" |
| `test_resolved_event_ignored` | Only active errors | Assert no task |
| `test_task_contains_error_context` | Debug info preserved | Assert stacktrace, affected users in metadata |

### 2.5 Loop Prevention Business Logic

**File:** `test_loop_prevention.py`

Tests the mechanism that prevents agents from responding to their own messages.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_agent_posted_comment_tracked` | Comments tracked | Assert comment_id in Redis |
| `test_subsequent_webhook_for_own_comment_ignored` | No self-response | Assert no task created |
| `test_tracking_expires_after_1_hour` | TTL prevents stale data | Assert not found after 1 hour |
| `test_different_comment_not_blocked` | Only exact match blocked | Assert task created for new comment |

**How Loop Prevention Works:**
```
1. Agent posts comment to GitHub/Jira
   ├── Store comment_id in Redis: "posted_comments:{comment_id}"
   └── TTL: 1 hour

2. Webhook received for that comment
   ├── Check Redis for comment_id
   ├── If found → Ignore (return 200, no task)
   └── If not found → Process normally

3. After 1 hour
   └── TTL expires, key deleted
```

**Behavior Test Example:**
```python
async def test_loop_prevention_flow():
    """Business requirement: Agent doesn't respond to its own comments"""
    # Agent posts a comment
    await agent.post_github_comment(
        repo="myorg/myrepo",
        issue_number=123,
        comment_id="comment-456",
        body="I've analyzed this issue..."
    )

    # Webhook received for that comment
    payload = github_issue_comment_payload(
        repo="myorg/myrepo",
        issue_number=123,
        comment_id="comment-456"
    )

    response = await webhook_handler.handle_github(payload, signature=valid_signature)
    assert response.status_code == 200
    assert response.body["action"] == "ignored"
    assert "loop prevention" in response.body["reason"]
```

---

## 3. Dashboard API Tests

Location: `dashboard-api/tests/`

### 3.1 Conversation Business Logic

**File:** `test_conversations.py`

Tests conversation tracking and metric aggregation.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_conversation_aggregates_task_metrics` | Roll-up metrics | Assert total_cost, total_tasks, total_duration correct |
| `test_conversation_started_at_is_earliest_task` | Timeline accuracy | Assert started_at == min(task.started_at) |
| `test_conversation_completed_at_is_latest_task` | Timeline accuracy | Assert completed_at == max(task.completed_at) |
| `test_messages_ordered_chronologically` | Readable history | Assert messages sorted by created_at |
| `test_archived_conversation_excluded_from_active` | Archive behavior | Assert archived conversations not in active list |
| `test_task_completion_updates_conversation` | Real-time metrics | Assert metrics update when task completes |

**Behavior Test Example:**
```python
async def test_conversation_metrics_aggregation():
    """Business requirement: Conversation metrics reflect all tasks"""
    conversation = create_conversation(title="Fix auth bug")

    task1 = create_task(conversation_id=conversation.id)
    task1.complete(cost_usd=0.10, duration_seconds=30)
    await conversation.add_task(task1)

    task2 = create_task(conversation_id=conversation.id)
    task2.complete(cost_usd=0.25, duration_seconds=60)
    await conversation.add_task(task2)

    task3 = create_task(conversation_id=conversation.id)
    task3.fail(error="Timeout")
    await conversation.add_task(task3)

    assert conversation.total_cost_usd == 0.35
    assert conversation.total_tasks == 3
    assert conversation.total_duration_seconds == 90
```

### 3.2 Webhook Configuration Business Logic

**File:** `test_webhook_config.py`

Tests webhook configuration management.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_static_webhooks_loaded_from_yaml` | Built-in webhooks work | Assert GitHub/Jira/Slack/Sentry loaded |
| `test_static_webhooks_immutable` | Cannot modify built-ins | Assert update raises error |
| `test_dynamic_webhook_crud` | User webhooks work | Assert create/read/update/delete work |
| `test_webhook_endpoint_format_validated` | URL safety | Assert `/webhooks/[a-z0-9-]+` enforced |
| `test_webhook_requires_commands` | Must have actions | Assert error if commands empty |
| `test_no_duplicate_command_names` | Command uniqueness | Assert error on duplicate |
| `test_default_command_must_exist` | Valid default | Assert error if default not in list |
| `test_command_requires_template` | Action definition | Assert error if no template |

**Webhook Configuration Rules:**
- Endpoint must match: `/webhooks/[a-z0-9-]+`
- Commands list cannot be empty
- No duplicate command names within webhook
- Default command must exist in commands list
- Either prompt_template or template_file required

### 3.3 Analytics Business Logic

**File:** `test_analytics.py`

Tests analytics calculations and aggregations.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_daily_cost_aggregation` | Cost trends | Assert sum matches individual tasks |
| `test_daily_task_count` | Volume trends | Assert count matches |
| `test_success_rate_calculation` | Quality metrics | Assert (completed / total) * 100 |
| `test_average_duration_calculation` | Performance metrics | Assert average of completed tasks |
| `test_cost_by_agent_breakdown` | Attribution | Assert per-agent costs sum to total |
| `test_cost_by_provider_breakdown` | Claude vs Cursor | Assert per-provider costs sum to total |

---

## 4. API Services Tests

Location: `api-services/*/tests/`

### 4.1 GitHub API Service

**File:** `github-api/tests/test_github_operations.py`

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_create_pull_request` | PR creation works | Assert PR URL returned |
| `test_create_pr_with_draft_flag` | Draft PRs supported | Assert PR is draft |
| `test_add_comment_to_issue` | Communication works | Assert comment created |
| `test_add_comment_to_pr` | PR feedback works | Assert comment created |
| `test_get_file_contents` | Code reading works | Assert content returned |
| `test_create_branch` | Branch creation works | Assert branch exists |
| `test_rate_limit_handled_gracefully` | Rate limit recovery | Assert retry after wait |
| `test_invalid_token_returns_401` | Auth failure clear | Assert 401 with message |

### 4.2 Jira API Service

**File:** `jira-api/tests/test_jira_operations.py`

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_get_issue_details` | Issue reading works | Assert all fields returned |
| `test_add_comment_to_issue` | Communication works | Assert comment created |
| `test_transition_issue` | Workflow works | Assert status changed |
| `test_search_issues_by_jql` | Search works | Assert matching issues returned |
| `test_update_issue_fields` | Editing works | Assert fields updated |
| `test_invalid_transition_rejected` | Workflow enforcement | Assert error for invalid transition |

### 4.3 Slack API Service

**File:** `slack-api/tests/test_slack_operations.py`

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_post_message_to_channel` | Messaging works | Assert message posted |
| `test_post_message_with_blocks` | Rich formatting works | Assert blocks rendered |
| `test_reply_in_thread` | Threading works | Assert message in thread |
| `test_get_channel_history` | Context retrieval works | Assert messages returned |
| `test_post_to_invalid_channel_fails` | Error handling | Assert error with channel info |

### 4.4 Sentry API Service

**File:** `sentry-api/tests/test_sentry_operations.py`

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_get_issue_details` | Issue reading works | Assert stacktrace, metadata returned |
| `test_add_comment_to_issue` | Communication works | Assert comment added |
| `test_update_issue_status` | Status management | Assert status changed |
| `test_get_affected_users` | Impact analysis | Assert user count returned |

---

## 5. MCP Servers Tests

Location: `mcp-servers/*/tests/`

### 5.1 Tool Registration

**File:** `test_mcp_tools.py`

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_github_mcp_registers_all_tools` | Tool discovery works | Assert all tools in list |
| `test_jira_mcp_registers_all_tools` | Tool discovery works | Assert all tools in list |
| `test_tool_descriptions_not_empty` | Useful docs | Assert description.length > 0 |
| `test_tool_parameters_typed` | Type safety | Assert all params have types |
| `test_tool_returns_structured_response` | Consistent responses | Assert response matches schema |

**Expected Tools by MCP Server:**
| Server | Tools |
|--------|-------|
| github-mcp | create_pull_request, get_file_contents, create_branch, add_comment, search_code |
| jira-mcp | get_issue, create_issue, update_issue, add_comment, search_issues, transition_issue |
| slack-mcp | post_message, get_conversations, list_channels, reply_in_thread |
| sentry-mcp | get_issue, add_comment, update_status, get_events |

### 5.2 MCP-to-API Service Integration

**File:** `test_mcp_api_integration.py`

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_github_mcp_calls_github_api` | Service routing works | Assert API service called |
| `test_jira_mcp_calls_jira_api` | Service routing works | Assert API service called |
| `test_api_error_propagated_to_agent` | Error visibility | Assert agent sees error |
| `test_api_timeout_handled` | Resilience | Assert graceful timeout handling |

---

## 6. Task Logger Tests

Location: `task-logger/tests/`

### 6.1 Event Processing Business Logic

**File:** `test_event_processing.py`

Tests the core event processing logic and routing.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_webhook_events_buffered_until_task_id_known` | Early events buffered | Assert events written once task_id available |
| `test_webhook_events_written_in_order` | Event ordering preserved | Assert chronological order in log file |
| `test_task_created_writes_metadata` | Metadata captured | Assert metadata.json contains all fields |
| `test_task_created_writes_input` | Initial input preserved | Assert 01-input.json matches source data |
| `test_task_output_appends_to_stream` | Streaming output captured | Assert all outputs in 03-agent-output.jsonl |
| `test_user_input_captured_separately` | User responses tracked | Assert user inputs in 03-user-inputs.jsonl |
| `test_task_completed_writes_final_result` | Success metrics captured | Assert cost, duration in final result |
| `test_task_failed_writes_error_details` | Failure debugging | Assert error details in final result |
| `test_invalid_event_type_logged_not_crashed` | Resilience | Assert warning logged, service continues |
| `test_missing_task_id_logged_not_crashed` | Resilience | Assert warning logged, service continues |

**Event Flow:**
```
Webhook Events (webhook_event_id):
  webhook:received → webhook:validated → webhook:matched → webhook:task_created
  (buffered until task_id known) → (written to 02-webhook-flow.jsonl)

Task Events (task_id):
  task:created → metadata.json + 01-input.json
  task:started → (marker event)
  task:output → 03-agent-output.jsonl (append)
  task:user_input → 03-user-inputs.jsonl (append)
  task:completed → 04-final-result.json
  task:failed → 04-final-result.json (with error)
```

**Behavior Test Example:**
```python
async def test_webhook_event_buffering():
    """Business requirement: Early webhook events buffered until task_id known"""
    webhook_event_id = "webhook-001"

    # Publish early webhook events (no task_id yet)
    await redis_client.xadd("task_events", {
        "type": "webhook:received",
        "webhook_event_id": webhook_event_id,
        "data": json.dumps({"provider": "github"})
    })

    await redis_client.xadd("task_events", {
        "type": "webhook:validated",
        "webhook_event_id": webhook_event_id,
        "data": json.dumps({"valid": True})
    })

    # No log files created yet
    await asyncio.sleep(0.1)
    assert not (logs_dir / "task-001" / "02-webhook-flow.jsonl").exists()

    # Publish event with task_id
    await redis_client.xadd("task_events", {
        "type": "webhook:task_created",
        "webhook_event_id": webhook_event_id,
        "data": json.dumps({"task_id": "task-001"})
    })

    # Wait for processing
    await asyncio.sleep(0.1)

    # All buffered events now written
    log_file = logs_dir / "task-001" / "02-webhook-flow.jsonl"
    assert log_file.exists()

    events = [json.loads(line) for line in log_file.read_text().splitlines()]
    assert len(events) == 3
    assert events[0]["stage"] == "received"
    assert events[1]["stage"] == "validated"
    assert events[2]["stage"] == "task_created"
```

### 6.2 Log Structure Business Logic

**File:** `test_log_structure.py`

Tests the structured logging format and file organization.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_task_directory_created_atomically` | Directory isolation | Assert directory exists for each task |
| `test_metadata_json_is_valid_json` | Machine readable | Assert json.loads() succeeds |
| `test_input_json_is_valid_json` | Machine readable | Assert json.loads() succeeds |
| `test_webhook_flow_jsonl_valid` | JSONL format | Assert each line is valid JSON |
| `test_agent_output_jsonl_valid` | JSONL format | Assert each line is valid JSON |
| `test_user_inputs_jsonl_valid` | JSONL format | Assert each line is valid JSON |
| `test_final_result_json_is_valid_json` | Machine readable | Assert json.loads() succeeds |
| `test_timestamps_are_iso8601_format` | Time tracking | Assert datetime.fromisoformat() succeeds |
| `test_log_files_have_correct_permissions` | Security | Assert files are 644, dirs are 755 |
| `test_atomic_writes_prevent_corruption` | Data integrity | Assert temp file + rename pattern |

**Log File Structure:**
```
/data/logs/tasks/{task_id}/
├── metadata.json              # Task metadata (source, agent, model)
├── 01-input.json             # Initial task input
├── 02-webhook-flow.jsonl     # Webhook processing stages
├── 03-agent-output.jsonl     # Claude output stream
├── 03-user-inputs.jsonl      # User responses
└── 04-final-result.json      # Final result + metrics
```

**Behavior Test Example:**
```python
def test_complete_log_structure():
    """Business requirement: Each task gets complete structured logs"""
    task_id = "task-001"
    task_dir = logs_dir / task_id

    # Process full task lifecycle
    process_task_events(task_id)

    # Verify all required files exist
    assert (task_dir / "metadata.json").exists()
    assert (task_dir / "01-input.json").exists()
    assert (task_dir / "02-webhook-flow.jsonl").exists()
    assert (task_dir / "03-agent-output.jsonl").exists()
    assert (task_dir / "03-user-inputs.jsonl").exists()
    assert (task_dir / "04-final-result.json").exists()

    # Verify JSON validity
    metadata = json.loads((task_dir / "metadata.json").read_text())
    assert "task_id" in metadata
    assert "source" in metadata
    assert "assigned_agent" in metadata

    # Verify JSONL validity
    webhook_events = [
        json.loads(line)
        for line in (task_dir / "02-webhook-flow.jsonl").read_text().splitlines()
    ]
    assert all("timestamp" in e for e in webhook_events)
    assert all("stage" in e for e in webhook_events)

    # Verify final result
    final_result = json.loads((task_dir / "04-final-result.json").read_text())
    assert "success" in final_result
    assert "completed_at" in final_result
```

### 6.3 Redis Stream Consumer Business Logic

**File:** `test_redis_consumer.py`

Tests the Redis stream consumer group behavior.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_consumer_group_created_on_startup` | Setup automation | Assert XINFO GROUPS shows task-logger |
| `test_events_processed_in_order` | FIFO guarantee | Assert logs reflect event order |
| `test_events_acknowledged_after_processing` | Reliable delivery | Assert pending count decreases |
| `test_failed_event_not_acknowledged` | Retry capability | Assert event remains in pending |
| `test_multiple_consumers_no_duplicates` | Horizontal scaling | Assert each event processed once |
| `test_consumer_handles_backpressure` | Performance | Assert batch processing works |
| `test_graceful_shutdown_completes_current_batch` | Data integrity | Assert no partial processing |

**Consumer Group Pattern:**
```
Redis Stream: task_events
  ├── Consumer Group: task-logger
  │   ├── Consumer: worker-1
  │   ├── Consumer: worker-2
  │   └── Consumer: worker-3
  └── Messages: XADD → XREADGROUP → XACK
```

**Behavior Test Example:**
```python
async def test_consumer_acknowledges_successful_processing():
    """Business requirement: Successfully processed events are ACKed"""
    # Publish event
    await redis_client.xadd("task_events", {
        "type": "task:created",
        "task_id": "task-001",
        "data": json.dumps({"source": "test"})
    })

    # Check pending before processing
    pending_info = await redis_client.xpending("task_events", "task-logger")
    pending_before = pending_info[0]  # Count

    # Wait for processing
    await asyncio.sleep(0.5)

    # Check pending after processing
    pending_info = await redis_client.xpending("task_events", "task-logger")
    pending_after = pending_info[0]

    # Event should be acknowledged (pending count decreased)
    assert pending_after == pending_before - 1

    # Verify log file created
    assert (logs_dir / "task-001" / "metadata.json").exists()
```

### 6.4 API Endpoints Business Logic

**File:** `test_api_endpoints.py`

Tests the FastAPI service endpoints.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_health_endpoint_returns_healthy` | Monitoring | Assert 200 with status:healthy |
| `test_get_task_logs_returns_all_files` | Log retrieval | Assert all log types in response |
| `test_get_nonexistent_task_returns_404` | Error handling | Assert 404 with clear message |
| `test_get_task_logs_returns_valid_json` | Data format | Assert response is valid JSON |
| `test_metrics_endpoint_returns_queue_stats` | Monitoring | Assert queue_depth, lag, processed |
| `test_metrics_queue_depth_accurate` | Accuracy | Assert matches XLEN task_events |
| `test_metrics_tasks_processed_accurate` | Accuracy | Assert matches directory count |

**API Endpoints:**
```
GET /health
  → {"status": "healthy", "service": "task-logger"}

GET /tasks/{task_id}/logs
  → {
      "metadata": {...},
      "input": {...},
      "webhook_flow": [...],
      "agent_output": [...],
      "user_inputs": [...],
      "final_result": {...}
    }

GET /metrics
  → {
      "queue_depth": 0,
      "queue_lag": 0,
      "tasks_processed": 42
    }
```

**Behavior Test Example:**
```python
async def test_get_task_logs_endpoint():
    """Business requirement: API returns complete task logs"""
    # Create task with logs
    task_id = "task-001"
    await process_complete_task(task_id)

    # Call API
    response = await client.get(f"/tasks/{task_id}/logs")

    assert response.status_code == 200
    logs = response.json()

    # Verify structure
    assert "metadata" in logs
    assert "input" in logs
    assert "webhook_flow" in logs
    assert "agent_output" in logs
    assert "user_inputs" in logs
    assert "final_result" in logs

    # Verify content
    assert logs["metadata"]["task_id"] == task_id
    assert logs["final_result"]["success"] is True
```

### 6.5 Performance & Reliability Business Logic

**File:** `test_performance.py`

Tests performance characteristics and reliability.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_processes_100_events_under_1_second` | Performance | Assert duration < 1.0s |
| `test_queue_lag_remains_low_under_load` | Responsiveness | Assert lag < 1s with 1000 events |
| `test_memory_usage_stable_over_time` | No memory leaks | Assert RSS growth < 10MB over 1000 tasks |
| `test_disk_usage_predictable` | Capacity planning | Assert ~1KB per event |
| `test_concurrent_writes_no_corruption` | Thread safety | Assert all events captured correctly |
| `test_handles_redis_disconnect_gracefully` | Resilience | Assert retries and reconnects |
| `test_handles_disk_full_gracefully` | Resilience | Assert logs error, continues after space |

**Performance Benchmarks:**
```
Event Processing: < 10ms per event
Batch Processing: < 100ms per 10 events
Queue Lag: < 1s under normal load
Memory: < 100MB for 10k tasks
Disk: ~1KB per event (~100KB per task)
```

**Behavior Test Example:**
```python
async def test_performance_under_load():
    """Business requirement: Handles high volume with low latency"""
    import time

    # Publish 1000 events
    start = time.time()

    for i in range(100):
        task_id = f"task-{i:03d}"
        for event_type in ["task:created", "task:started", "task:output",
                          "task:completed"]:
            await redis_client.xadd("task_events", {
                "type": event_type,
                "task_id": task_id,
                "data": json.dumps({"test": "data"})
            })

    # Wait for all processing
    while await get_queue_depth() > 0:
        await asyncio.sleep(0.1)

    duration = time.time() - start

    # Performance requirements
    assert duration < 5.0, "Should process 400 events in < 5s"

    # Check lag
    metrics = await client.get("/metrics")
    assert metrics.json()["queue_lag"] < 1, "Queue lag should be < 1s"

    # Verify all tasks processed
    assert metrics.json()["tasks_processed"] == 100
```

### 6.6 Integration with Agent Engine

**File:** `test_agent_engine_integration.py`

Tests integration between task logger and agent engine.

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_agent_engine_publishes_task_events` | Integration works | Assert events appear in stream |
| `test_webhook_handler_publishes_webhook_events` | Integration works | Assert events appear in stream |
| `test_dashboard_api_publishes_user_inputs` | Integration works | Assert user inputs captured |
| `test_complete_task_lifecycle_logged` | End-to-end | Assert all stages captured |
| `test_parallel_tasks_isolated` | Isolation | Assert logs don't mix |

**Integration Points:**
```
API Gateway (Webhooks)
  ├── publish webhook:received
  ├── publish webhook:validated
  ├── publish webhook:matched
  └── publish webhook:task_created

Agent Engine (Task Worker)
  ├── publish task:created
  ├── publish task:started
  ├── publish task:output (streaming)
  └── publish task:completed / task:failed

Dashboard API (User Input)
  └── publish task:user_input
```

---

## 7. OAuth Service Tests

Location: `oauth-service/tests/`

### 6.1 Token Management Business Logic

**File:** `test_oauth_business_logic.py`

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_token_refresh_before_expiry` | Seamless auth | Assert refresh when < 30 min remaining |
| `test_expired_token_triggers_reauth` | Recovery flow | Assert redirect to auth |
| `test_installation_tracking` | Multi-tenant support | Assert installation stored |
| `test_credential_status_tracking` | Health monitoring | Assert status reflects reality |
| `test_rate_limited_token_marked` | Visibility | Assert status == RATE_LIMITED |

**Token Status Values:**
- `VALID` - Token is working
- `EXPIRED` - Token has expired
- `REFRESH_NEEDED` - Token expires within 30 minutes
- `MISSING` - No token available
- `RATE_LIMITED` - Token is rate limited

---

## 7. Integration Tests

Location: `tests/integration/`

### 7.1 End-to-End Workflow Tests

**File:** `test_e2e_workflows.py`

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_github_issue_to_pr_workflow` | Issue → PR flow | Assert PR created for issue |
| `test_jira_ticket_to_implementation` | Jira → Code flow | Assert code changes made |
| `test_sentry_error_to_fix` | Error → Fix flow | Assert fix committed |
| `test_slack_command_execution` | Slack → Result flow | Assert response posted |

**Behavior Test Example:**
```python
async def test_github_issue_triggers_pr_creation():
    """Business requirement: Issues with AI-Fix trigger automated PRs"""
    # 1. Simulate GitHub webhook for new issue
    issue_payload = github_issue_opened_payload(
        repo="myorg/myrepo",
        issue_number=42,
        title="Fix null pointer in user service",
        labels=["AI-Fix", "bug"]
    )

    # 2. Webhook creates task
    webhook_response = await api_gateway.handle_github(issue_payload)
    assert webhook_response.status_code == 202
    task_id = webhook_response.json()["task_id"]

    # 3. Wait for task completion (with timeout)
    task = await wait_for_task_completion(task_id, timeout=300)
    assert task.status == TaskStatus.COMPLETED

    # 4. Verify PR was created
    pr = await github_api.get_pull_request(
        repo="myorg/myrepo",
        head="fix/issue-42"  # Expected branch naming
    )
    assert pr is not None
    assert "null pointer" in pr.body.lower()
    assert pr.linked_issues == [42]
```

### 7.2 Service Communication Tests

**File:** `test_service_integration.py`

| Test Case | Business Requirement | Verification |
|-----------|---------------------|--------------|
| `test_agent_engine_to_mcp_server` | Tool access works | Assert tools callable |
| `test_mcp_server_to_api_service` | API access works | Assert operations succeed |
| `test_api_gateway_to_redis_queue` | Queueing works | Assert task queued |
| `test_redis_to_agent_engine` | Task pickup works | Assert task processed |
| `test_dashboard_websocket_updates` | Real-time works | Assert status broadcasted |
| `test_task_logger_captures_complete_flow` | End-to-end logging | Assert all events logged |
| `test_webhook_to_task_logger_integration` | Event publishing | Assert webhook events captured |
| `test_agent_engine_to_task_logger_integration` | Event publishing | Assert task events captured |

---

## 8. Test Fixtures & Factories

### 8.1 Shared Fixtures (`tests/conftest.py`)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from fakeredis import FakeRedis

@pytest.fixture
def mock_redis():
    """In-memory Redis for testing"""
    return FakeRedis()

@pytest.fixture
def mock_postgres():
    """In-memory PostgreSQL for testing (using SQLite)"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    return Session()

@pytest.fixture
def test_settings():
    """Test environment settings"""
    from config.settings import Settings
    return Settings(
        cli_provider="claude",
        redis_url="redis://localhost:6379/15",
        database_url="postgresql://test:test@localhost/test"
    )

@pytest.fixture
def github_webhook_signature():
    """Valid GitHub webhook signature generator"""
    import hmac
    import hashlib

    def _sign(payload: bytes, secret: str) -> str:
        return "sha256=" + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

    return _sign

@pytest.fixture
def jira_webhook_signature():
    """Valid Jira webhook signature generator"""
    # Similar to GitHub
    pass
```

### 8.2 Payload Factories (`tests/fixtures/`)

**github_payloads.py:**
```python
def github_issue_opened_payload(
    repo: str = "test/repo",
    issue_number: int = 1,
    title: str = "Test Issue",
    body: str = "Test body",
    labels: list[str] | None = None,
    user: str = "testuser"
) -> dict:
    return {
        "action": "opened",
        "issue": {
            "number": issue_number,
            "title": title,
            "body": body,
            "labels": [{"name": l} for l in (labels or [])],
            "user": {"login": user}
        },
        "repository": {
            "full_name": repo
        }
    }

def github_pr_opened_payload(
    repo: str = "test/repo",
    pr_number: int = 1,
    title: str = "Test PR",
    body: str = "Test body",
    head: str = "feature-branch",
    base: str = "main",
    user: str = "testuser"
) -> dict:
    return {
        "action": "opened",
        "pull_request": {
            "number": pr_number,
            "title": title,
            "body": body,
            "head": {"ref": head},
            "base": {"ref": base},
            "user": {"login": user}
        },
        "repository": {
            "full_name": repo
        }
    }

def github_issue_comment_payload(
    repo: str = "test/repo",
    issue_number: int = 1,
    comment_id: int = 100,
    body: str = "Test comment",
    user: str = "testuser"
) -> dict:
    return {
        "action": "created",
        "issue": {
            "number": issue_number
        },
        "comment": {
            "id": comment_id,
            "body": body,
            "user": {"login": user}
        },
        "repository": {
            "full_name": repo
        }
    }
```

**jira_payloads.py:**
```python
def jira_issue_created_payload(
    issue_key: str = "PROJ-123",
    summary: str = "Test Issue",
    description: str = "Test description",
    labels: list[str] | None = None,
    project: str = "PROJ"
) -> dict:
    return {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": issue_key,
            "fields": {
                "summary": summary,
                "description": description,
                "labels": [{"name": l} for l in (labels or [])],
                "project": {"key": project}
            }
        }
    }

def jira_comment_created_payload(
    issue_key: str = "PROJ-123",
    comment_id: str = "10001",
    body: str = "Test comment",
    author: str = "testuser"
) -> dict:
    return {
        "webhookEvent": "comment_created",
        "issue": {
            "key": issue_key
        },
        "comment": {
            "id": comment_id,
            "body": body,
            "author": {"displayName": author}
        }
    }
```

---

## 9. Test Execution Commands

### Running Tests

```bash
# Run all tests
cd agent-bot && make test

# Run unit tests only (fast)
cd agent-bot && make test-unit

# Run integration tests
cd agent-bot && make test-integration

# Run tests for specific service
pytest agent-engine/tests/ -v
pytest api-gateway/tests/ -v
pytest dashboard-api/tests/ -v

# Run specific test file
pytest agent-engine/tests/test_task_lifecycle.py -v

# Run with coverage
cd agent-bot && make coverage
```

### Test Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests", "agent-engine/tests", "api-gateway/tests", "dashboard-api/tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["agent-engine", "api-gateway", "dashboard-api"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError"
]
```

---

## 10. Success Criteria

### Coverage Targets

| Module | Target Coverage |
|--------|-----------------|
| Task lifecycle | 100% |
| Session management | 90% |
| Webhook handlers | 95% |
| Loop prevention | 100% |
| Task logger event processing | 95% |
| Task logger log structure | 100% |
| Conversation aggregation | 90% |
| Analytics calculations | 90% |

### Quality Criteria

- [ ] All task status transitions tested
- [ ] All webhook event types tested
- [ ] All task logger event types tested
- [ ] Task logger log structure validated
- [ ] Task logger Redis consumer tested
- [ ] Session/conversation aggregation tested
- [ ] Loop prevention tested
- [ ] All API operations have integration tests
- [ ] Tests run in < 5 seconds per file
- [ ] No real network calls in unit tests
- [ ] No flaky tests (100% deterministic)

---

## 11. Implementation Phases

### Phase 1: Core Business Logic (Week 1)
1. Create `tests/conftest.py` with shared fixtures
2. Create payload factories
3. Implement task lifecycle tests
4. Implement session management tests

### Phase 2: Webhook Processing (Week 2)
1. GitHub webhook tests
2. Jira webhook tests
3. Slack/Sentry webhook tests
4. Loop prevention tests

### Phase 3: Service Integration (Week 3)
1. Dashboard API tests (conversations, analytics)
2. Webhook configuration tests
3. API service tests (GitHub, Jira, Slack, Sentry)
4. Task logger tests (event processing, log structure)

### Phase 4: End-to-End Workflows (Week 4)
1. Full workflow integration tests
2. Cross-service communication tests
3. Task logger integration tests
4. Performance validation

---

## Appendix: Business Rules Reference

### Task Status State Machine

```python
VALID_TRANSITIONS = {
    TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.WAITING_INPUT, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.WAITING_INPUT: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),  # Terminal state
    TaskStatus.FAILED: set(),     # Terminal state
    TaskStatus.CANCELLED: set(),  # Terminal state
}
```

### Webhook Event Processing Rules

| Provider | Event | Filter | Action |
|----------|-------|--------|--------|
| GitHub | issues.opened | none | Create task |
| GitHub | issues.labeled | AI-Fix label | Create task |
| GitHub | issue_comment.created | not bot | Create task |
| GitHub | pull_request.opened | none | Create task |
| Jira | issue_created | AI-Fix label | Create task |
| Jira | issue_updated | AI-Fix label | Create task |
| Slack | app_mention | none | Create task |
| Sentry | issue.created | not resolved | Create task |

### Cost Calculation

```python
def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    PRICING = {
        "claude-opus-4": {"input": 15.0, "output": 75.0},  # per million tokens
        "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    }
    rates = PRICING.get(model, PRICING["claude-sonnet-4"])
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
```

### Task Logger Event Types

**Webhook Events:**
```python
class WebhookEventType(StrEnum):
    RECEIVED = "webhook:received"      # Raw webhook payload received
    VALIDATED = "webhook:validated"    # Signature verified
    MATCHED = "webhook:matched"        # Command matched
    TASK_CREATED = "webhook:task_created"  # Task queued
```

**Task Events:**
```python
class TaskEventType(StrEnum):
    CREATED = "task:created"          # Task metadata
    STARTED = "task:started"          # Execution begins
    OUTPUT = "task:output"            # Streaming agent output
    USER_INPUT = "task:user_input"    # User responds to question
    COMPLETED = "task:completed"      # Final results + metrics
    FAILED = "task:failed"            # Error details
```

**Event Processing Rules:**
```python
# Webhook events are buffered until task_id is known
if event_type.startswith("webhook:"):
    if "task_id" not in data:
        # Buffer in memory
        webhook_buffer[webhook_event_id].append(event)
    else:
        # Write buffered events + current event
        write_buffered_and_current_to_log(task_id, webhook_event_id, event)

# Task events are processed immediately
if event_type.startswith("task:"):
    if event_type == "task:created":
        write_metadata_and_input(task_id, data)
    elif event_type == "task:output":
        append_to_agent_output_log(task_id, data)
    elif event_type == "task:user_input":
        append_to_user_inputs_log(task_id, data)
    elif event_type in ["task:completed", "task:failed"]:
        write_final_result(task_id, data)
```

**Log File Mapping:**
```python
EVENT_TO_LOG_FILE = {
    "webhook:*": "02-webhook-flow.jsonl",
    "task:created": "metadata.json + 01-input.json",
    "task:output": "03-agent-output.jsonl",
    "task:user_input": "03-user-inputs.jsonl",
    "task:completed": "04-final-result.json",
    "task:failed": "04-final-result.json"
}
```
