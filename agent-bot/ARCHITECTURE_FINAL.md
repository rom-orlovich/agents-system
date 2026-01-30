# Agent Bot - Final Architecture

## Overview

Agent Bot is a production-ready webhook-driven AI agent system with **immediate webhook responses**, **streaming logs** (like Claude Code), and **direct result posting** to external services (GitHub, Jira, Slack, Sentry).

## Key Principles

1. **Immediate Response**: Webhooks return 200 OK instantly (no waiting for agent)
2. **Async Processing**: Tasks queued in Redis, processed by worker pool
3. **Streaming Logs**: Real-time progress tracking like Claude Code
4. **Direct Posting**: Agent posts final result directly to GitHub PR, Slack thread, etc.
5. **DRY**: Shared client packages in `integrations/` monorepo
6. **Strict Types**: NO `any` types, Pydantic with `strict=True` everywhere

## High-Level Request Flow

```
1. GitHub webhook arrives
   POST /webhooks/github
        │
        ▼
2. API Gateway (IMMEDIATE RESPONSE - NO WAITING)
   ├─► Validate signature (HMAC SHA256)
   ├─► Parse payload (Pydantic validation)
   ├─► Extract command (@agent analyze)
   ├─► Create task (task_id: task-abc123)
   ├─► Enqueue to Redis queue
   └─► RETURN 200 OK {"task_id": "task-abc123"} ✅ INSTANT
        │
        ▼
3. Agent Container (ASYNC - processes in background)
   ├─► Dequeue task from Redis
   ├─► Start streaming logger (stream.jsonl)
   ├─► Execute CLI (claude or cursor)
   ├─► Stream progress logs in real-time:
   │   ├─ "initialization: Task received"
   │   ├─ "execution: Starting CLI execution"
   │   ├─ "execution: CLI execution completed"
   │   ├─ "posting_result: Posting result to github"
   │   └─ "completion: Task completed successfully"
   ├─► Get final result from CLI
   ├─► Post result DIRECTLY to GitHub PR via MCP:
   │   └─► github_post_pr_comment(repo, pr_number, comment)
   └─► Add reaction emoji:
       └─► github_add_pr_reaction(repo, pr_number, "rocket")
```

## Architecture Components

### 1. API Gateway (Port 8080)

**Purpose**: Webhook receiver, returns **immediately**

```
api-gateway/
├── webhooks/
│   ├── github_handler.py      # Separate handler per provider
│   ├── jira_handler.py         # NO if/else chains
│   ├── slack_handler.py
│   ├── sentry_handler.py
│   └── signature_validator.py  # HMAC validation
├── queue/
│   └── redis_queue.py          # Priority-based queue (sorted set)
└── core/
    └── task_logger.py          # Centralized JSONL logging
```

**Key Flow**:
```python
async def handle(payload, headers) -> WebhookResponse:
    task_id = generate_task_id()

    validate_signature(payload, headers)

    validated = GitHubWebhookPayload.model_validate(payload)

    task = TaskQueueMessage(task_id=task_id, input_message=extract_message())

    await task_queue.enqueue(task)

    return WebhookResponse(
        success=True,
        task_id=task_id,
        message="Task created and queued"
    )
```

**IMPORTANT**: Returns immediately, does NOT wait for agent!

### 2. Agent Container

**Purpose**: Process tasks asynchronously, stream logs, post results directly

```
agent-container/
├── workers/
│   └── task_worker.py          # Main worker loop
├── core/
│   ├── streaming_logger.py     # Real-time streaming (like Claude Code)
│   ├── result_poster.py        # Posts to GitHub/Jira/Slack/Sentry via MCP
│   ├── mcp_client.py           # MCP client for calling tools
│   ├── task_logger.py          # JSONL logger
│   └── cli_runner/
│       ├── claude_cli_runner.py
│       └── cursor_cli_runner.py
└── .claude/
    ├── skills/
    ├── agents/
    ├── rules/
    └── commands/
```

**Key Flow**:
```python
async def process_task(task_data, mcp_client):
    streaming_logger = StreamingLogger(task_id)

    await streaming_logger.log_progress(
        stage="initialization",
        message="Task received by agent"
    )

    result = await cli_runner.execute(prompt, model, agents)

    await streaming_logger.log_progress(
        stage="posting_result",
        message=f"Posting result to {provider}"
    )

    result_poster = ResultPoster(mcp_client)
    await result_poster.post_result(
        provider=WebhookProvider.GITHUB,
        metadata={"repository": "owner/repo", "pr_number": 42},
        result=result.output
    )

    await streaming_logger.log_completion(success=True)
```

**IMPORTANT**: Agent posts result directly to external service (NOT back to API Gateway)!

### 3. Streaming Logger

**Purpose**: Real-time progress tracking like Claude Code

**Stream File**: `/data/logs/tasks/{task_id}/stream.jsonl`

**Events**:
```jsonl
{"timestamp":"2026-01-30T10:00:00Z","event_type":"progress","stage":"initialization","message":"Task received by agent"}
{"timestamp":"2026-01-30T10:00:01Z","event_type":"progress","stage":"execution","message":"Starting CLI execution"}
{"timestamp":"2026-01-30T10:00:05Z","event_type":"cli_output","line":"Running tests...","stream":"stdout"}
{"timestamp":"2026-01-30T10:00:10Z","event_type":"progress","stage":"execution","message":"CLI execution completed","success":true}
{"timestamp":"2026-01-30T10:00:11Z","event_type":"mcp_call","tool_name":"github_post_pr_comment","arguments":{"pr_number":42}}
{"timestamp":"2026-01-30T10:00:12Z","event_type":"mcp_result","tool_name":"github_post_pr_comment","success":true}
{"timestamp":"2026-01-30T10:00:13Z","event_type":"completion","success":true,"result":"Analysis complete"}
```

**Dashboard Integration**:
```bash
# Tail stream in real-time
tail -f /data/logs/tasks/task-abc123/stream.jsonl

# Or via API
GET /api/v1/tasks/task-abc123/stream
```

### 4. Result Poster

**Purpose**: Post final results directly to external services via MCP

**Supported Providers**:
- ✅ **GitHub**: Post PR comment + add reaction emoji
- ✅ **Jira**: Add comment to issue
- ✅ **Slack**: Post message (with thread support)
- ✅ **Sentry**: Add comment to issue

**Example**:
```python
result_poster = ResultPoster(mcp_client)

await result_poster.post_result(
    provider=WebhookProvider.GITHUB,
    metadata={
        "repository": "owner/repo",
        "pr_number": 42,
        "action": "pull_request"
    },
    result="## Analysis Complete\n\nNo issues found. Ready to merge!"
)
```

**Internally calls**:
```python
await mcp_client.call_tool(
    name="github_post_pr_comment",
    arguments={
        "owner": "owner",
        "repo": "repo",
        "pr_number": 42,
        "comment": "## Agent Result\n\n## Analysis Complete..."
    }
)

await mcp_client.call_tool(
    name="github_add_pr_reaction",
    arguments={"owner": "owner", "repo": "repo", "pr_number": 42, "reaction": "rocket"}
)
```

### 5. Integrations Monorepo (DRY Principle)

**Purpose**: Shared API clients consumed by MCP servers and REST APIs

```
integrations/
├── jira_client/           # Shared Jira API client
│   ├── jira_client/
│   │   ├── client.py      # JiraClient class
│   │   ├── models.py      # Pydantic models (strict=True)
│   │   └── exceptions.py  # Custom exceptions
│   └── tests/
├── jira_mcp_server/       # MCP server (depends on jira_client)
│   ├── jira_mcp_server/
│   │   └── server.py      # FastMCP server
│   └── Dockerfile         # Multi-stage with uv
├── jira_rest_api/         # REST API (depends on jira_client)
│   ├── jira_rest_api/
│   │   └── routes.py      # FastAPI routes
│   └── Dockerfile         # Multi-stage with uv
```

**DRY Architecture**:
```
                    jira_client (shared)
                           │
           ┌───────────────┴───────────────┐
           │                               │
    jira_mcp_server                 jira_rest_api
    (stdio for agents)              (HTTP for services)
```

**Same for**:
- `slack_client` → `slack_mcp_server` + `slack_rest_api`
- `sentry_client` → `sentry_mcp_server` + `sentry_rest_api`

## Complete Request Flow Example

### GitHub PR Comment with @agent

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. User comments on PR #42: "@agent analyze this code"             │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. GitHub sends webhook POST /webhooks/github                       │
│    Headers: X-Hub-Signature-256: sha256=...                         │
│    Body: {"action": "created", "pull_request": {...}, ...}          │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. API Gateway (github_handler.py)                                  │
│    • Validate HMAC signature ✅                                      │
│    • Parse with GitHubWebhookPayload ✅                              │
│    • Extract command: "@agent analyze this code" ✅                 │
│    • Create task: task-abc123 ✅                                     │
│    • Enqueue to Redis queue ✅                                       │
│    • RETURN 200 OK {"task_id": "task-abc123"} ⚡ IMMEDIATE          │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. Redis Queue (sorted set by priority)                             │
│    ZADD tasks 1.0 '{"task_id":"task-abc123",...}'                   │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. Agent Container Worker (task_worker.py)                          │
│    • Dequeue: BZPOPMIN tasks                                        │
│    • Create StreamingLogger(task-abc123)                            │
│    • Log: "initialization: Task received" ✅                         │
│                                                                      │
│    • Execute CLI Runner:                                            │
│      claude code --prompt "analyze this code" --model opus          │
│                                                                      │
│    • Stream progress:                                               │
│      ├─ "execution: Starting CLI execution"                         │
│      ├─ "cli_output: Reading files..."                              │
│      ├─ "cli_output: Running analysis..."                           │
│      └─ "execution: CLI execution completed" ✅                      │
│                                                                      │
│    • Get result: "Code looks good, no issues found"                 │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. Result Poster (result_poster.py)                                 │
│    • Log: "posting_result: Posting to github"                       │
│    • Call MCP Client:                                               │
│      await mcp_client.call_tool(                                    │
│        name="github_post_pr_comment",                               │
│        arguments={                                                  │
│          "owner": "owner",                                          │
│          "repo": "repo",                                            │
│          "pr_number": 42,                                           │
│          "comment": "## Agent Result\n\nCode looks good!"           │
│        }                                                            │
│      )                                                              │
│    • Log: "posting_result: Successfully posted" ✅                   │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. GitHub MCP Server (official)                                     │
│    • Receives MCP call via stdio                                    │
│    • Calls GitHub API:                                              │
│      POST /repos/owner/repo/issues/42/comments                      │
│      {"body": "## Agent Result\n\nCode looks good!"}                │
│    • Returns success ✅                                              │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 8. GitHub PR shows comment:                                         │
│    @agent-bot: ## Agent Result                                      │
│                Code looks good, no issues found. Ready to merge! 🚀 │
└─────────────────────────────────────────────────────────────────────┘
```

## Docker Compose Services

```yaml
services:
  # Infrastructure
  redis: Port 6379
  postgres: Port 5432

  # Core Services
  api-gateway: Port 8080          # Webhook receiver (immediate response)
  agent-container: No port        # Background worker (2 replicas)
  dashboard-api: Port 8090        # Log viewer, analytics

  # MCP Servers (stdio only - for agents)
  github-mcp-server: stdio
  jira-mcp-server: stdio
  slack-mcp-server: stdio
  sentry-mcp-server: stdio

  # REST APIs (HTTP - for dashboard and other services)
  jira-rest-api: Port 8082
  slack-rest-api: Port 8083
  sentry-rest-api: Port 8084
```

## Benefits of This Architecture

1. **Fast Webhook Response**: GitHub/Jira/Slack webhooks timeout after 10s - we respond in <100ms ✅
2. **Real-Time Visibility**: Stream logs show progress like Claude Code ✅
3. **User Experience**: Results appear directly in the PR/Issue where user commented ✅
4. **Scalability**: Queue-based, can scale agent workers independently ✅
5. **DRY**: Shared clients mean one place to fix bugs ✅
6. **Type Safety**: Pydantic strict mode catches errors early ✅
7. **Testability**: Each component testable in isolation ✅

## Directory Structure

```
agent-bot/
├── api-gateway/              # Webhook receiver (immediate response)
├── agent-container/          # Task processor (async, streaming)
├── dashboard-api-container/  # Log viewer, analytics
├── integrations/             # Monorepo (shared clients + servers)
│   ├── jira_client/
│   ├── jira_mcp_server/
│   ├── jira_rest_api/
│   ├── slack_client/
│   ├── slack_mcp_server/
│   ├── slack_rest_api/
│   ├── sentry_client/
│   ├── sentry_mcp_server/
│   └── sentry_rest_api/
└── docker-compose.yml        # All services (no deprecated version field)
```

## Key Files

- `api-gateway/webhooks/github_handler.py` - Immediate webhook response
- `agent-container/workers/task_worker.py` - Async task processing + result posting
- `agent-container/core/streaming_logger.py` - Real-time streaming (like Claude Code)
- `agent-container/core/result_poster.py` - Direct posting to GitHub/Jira/Slack/Sentry
- `agent-container/core/mcp_client.py` - MCP client for calling tools
- `integrations/*/client.py` - Shared API clients (DRY principle)
