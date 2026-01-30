# MCP Architecture - Model Context Protocol Integration

## Overview

This document explains how MCP (Model Context Protocol) servers are integrated into the agent-bot system and where each component lives.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│  External Services                                           │
│  (GitHub API, Jira API, Slack API, Sentry API)              │
└────────────────────────▲─────────────────────────────────────┘
                         │
                         │ HTTPS API Calls
                         │
┌────────────────────────┴─────────────────────────────────────┐
│  MCP Servers (Separate Containers)                           │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │   GitHub    │  │  Jira    │  │  Slack   │  │  Sentry  │ │
│  │  MCP Server │  │MCP Server│  │MCP Server│  │MCP Server│ │
│  │  (Node.js)  │  │ (Python) │  │ (Python) │  │ (Python) │ │
│  └──────▲──────┘  └─────▲────┘  └─────▲────┘  └─────▲────┘ │
└─────────┼───────────────┼────────────┼───────────────┼──────┘
          │               │            │               │
          │ stdio/SSE     │            │               │
          │               │            │               │
┌─────────┴───────────────┴────────────┴───────────────┴──────┐
│  Agent Container                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  MCP Client Library                                  │   │
│  │  - Connects to MCP servers via stdio                 │   │
│  │  - Calls tools: github_post_pr_comment, etc.         │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Claude CLI / Cursor CLI                             │   │
│  │  - Executes tasks from queue                         │   │
│  │  - Uses MCP tools via client                         │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Task Worker                                          │   │
│  │  - Dequeues tasks from Redis                         │   │
│  │  - Processes using CLI runner                        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────▲─────────────────────────────────────┘
                         │
                         │ Dequeue Tasks
                         │
┌────────────────────────┴─────────────────────────────────────┐
│  Redis Queue                                                 │
│  - Stores pending tasks                                      │
│  - Priority-based ordering                                   │
└────────────────────────▲─────────────────────────────────────┘
                         │
                         │ Enqueue Tasks
                         │
┌────────────────────────┴─────────────────────────────────────┐
│  API Gateway                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   GitHub     │  │    Jira      │  │    Slack     │       │
│  │   Handler    │  │   Handler    │  │   Handler    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  - Receives webhooks                                         │
│  - Validates signatures                                      │
│  - Creates tasks                                             │
│  - Does NOT contain MCP servers                              │
└────────────────────────▲─────────────────────────────────────┘
                         │
                         │ Webhook Requests
                         │
┌────────────────────────┴─────────────────────────────────────┐
│  External Webhook Sources                                    │
│  (GitHub, Jira, Slack, Sentry)                               │
└──────────────────────────────────────────────────────────────┘
```

## Component Locations

### 1. API Gateway Container
**Location**: `api-gateway/`

**What Lives Here**:
- Webhook handlers (GitHub, Jira, Slack, Sentry)
- Signature validators
- Task queue client
- Task logger
- HTTP server (FastAPI)

**What Does NOT Live Here**:
- MCP servers
- MCP client
- External API calls

**Role**: Receive webhooks → Validate → Create tasks → Enqueue

---

### 2. MCP Server Containers (4 separate containers)
**Location**: `github-mcp-server/`, `jira-mcp-server/`, `slack-mcp-server/`, `sentry-mcp-server/`

**What Lives Here**:
- MCP server implementation
- External API clients (httpx)
- Pydantic models for tool inputs
- Tool implementations

**Communication**:
- **Input**: stdio from agent-container
- **Output**: TextContent responses
- **External**: HTTPS calls to GitHub/Jira/Slack/Sentry APIs

**GitHub MCP Server**:
```
github-mcp-server/
├── Dockerfile (uses official github/github-mcp-server)
└── Built from: https://github.com/github/github-mcp-server
```

**Other MCP Servers**:
```
{service}-mcp-server/
├── Dockerfile (Python 3.11)
├── server.py (FastMCP implementation)
└── requirements.txt (mcp, pydantic, httpx, structlog)
```

**Tools Provided**:
- GitHub: `github_post_pr_comment`, `github_add_pr_reaction`
- Jira: `jira_add_comment`, `jira_get_issue`, `jira_create_issue`, `jira_transition_issue`
- Slack: `slack_post_message`, `slack_update_message`, `slack_add_reaction`
- Sentry: `sentry_add_comment`, `sentry_update_status`, `sentry_get_issue`, `sentry_assign_issue`, `sentry_add_tag`

---

### 3. Agent Container
**Location**: `agent-container/`

**What Lives Here**:
- **MCP Client Library** (connects to MCP servers)
- Task worker (dequeues from Redis)
- CLI runner (Claude CLI or Cursor CLI)
- Claude Code configuration (`.claude/`)

**What Does NOT Live Here**:
- MCP server implementations
- External API clients

**Role**: Dequeue tasks → Execute with CLI → Use MCP tools → Log results

**Environment Variables**:
```bash
MCP_GITHUB_HOST=github-mcp-server   # Hostname of GitHub MCP server
MCP_JIRA_HOST=jira-mcp-server
MCP_SLACK_HOST=slack-mcp-server
MCP_SENTRY_HOST=sentry-mcp-server
```

**MCP Client Usage**:
```python
# Inside agent-container
from mcp import Client

# Connect to GitHub MCP server
async with Client(host=os.getenv("MCP_GITHUB_HOST")) as github_client:
    # Call tool
    result = await github_client.call_tool(
        "github_post_pr_comment",
        {
            "owner": "org",
            "repo": "repo",
            "pr_number": 123,
            "comment": "LGTM!"
        }
    )
```

---

## Data Flow

### Complete Webhook → Tool Call Flow

1. **Webhook Received**:
   ```
   GitHub → POST /webhooks/github → API Gateway
   ```

2. **Webhook Processed**:
   ```
   API Gateway:
   - github_handler.py receives payload
   - Validates signature
   - Extracts "@agent review" command
   - Creates Task object
   ```

3. **Task Queued**:
   ```
   API Gateway → Redis Queue
   - Task stored with priority
   - TaskLogger creates log files
   ```

4. **Task Dequeued**:
   ```
   Agent Container:
   - Worker polls Redis queue
   - Dequeues task
   - Passes to CLI runner
   ```

5. **CLI Executes**:
   ```
   Agent Container:
   - Claude CLI processes task
   - Determines need to post PR comment
   - Uses MCP client to call tool
   ```

6. **MCP Tool Called**:
   ```
   Agent Container → GitHub MCP Server (stdio)
   Request: {
     "tool": "github_post_pr_comment",
     "arguments": {
       "owner": "org",
       "repo": "repo",
       "pr_number": 123,
       "comment": "Analysis complete. LGTM!"
     }
   }
   ```

7. **MCP Server Executes**:
   ```
   GitHub MCP Server:
   - Validates arguments (Pydantic)
   - Calls GitHub API
   - Returns TextContent
   ```

8. **Response Returned**:
   ```
   GitHub MCP Server → Agent Container
   Response: [TextContent("Successfully posted comment...")]
   ```

9. **Result Logged**:
   ```
   Agent Container:
   - TaskLogger.write_final_result()
   - Marks task complete
   ```

---

## Why This Architecture?

### Separation of Concerns ✅
- **API Gateway**: Webhooks only
- **MCP Servers**: External API calls only
- **Agent Container**: Task execution only

### Independent Scaling ✅
```yaml
# Scale agents independently
agent-container:
  deploy:
    replicas: 5  # Can scale up/down

# MCP servers scale based on load
github-mcp-server:
  deploy:
    replicas: 2
```

### Type Safety ✅
All MCP tool inputs are validated:
```python
class PostPRCommentInput(BaseModel):
    model_config = ConfigDict(strict=True)  # NO loose types!
    owner: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    pr_number: int = Field(..., gt=0)
    comment: str = Field(..., min_length=1)
```

### Protocol Standardization ✅
- All tools use same MCP protocol
- Easy to add new tools
- Claude Code native support

### Testability ✅
- Mock MCP servers for testing
- Test webhooks independently
- Test agents independently

---

## Configuration

### Docker Compose
```yaml
# MCP servers run as separate containers
github-mcp-server:
  build: ./github-mcp-server
  environment:
    - GITHUB_TOKEN=${GITHUB_TOKEN}
  stdin_open: true   # Required for stdio
  tty: true          # Required for stdio

# Agent container connects to MCP servers
agent-container:
  build: ./agent-container
  environment:
    - MCP_GITHUB_HOST=github-mcp-server  # Connect via hostname
  depends_on:
    - github-mcp-server  # Ensure MCP servers start first
```

### Webhooks Still Use HTTP
Webhooks from external sources (GitHub, Jira, etc.) still come via HTTP to API Gateway:
```
GitHub Webhook → HTTPS → API Gateway:8080/webhooks/github
```

MCP is ONLY used for tool calls FROM agents TO external services.

---

## FAQ

### Q: Do MCP servers live inside API Gateway?
**A**: NO. MCP servers are separate containers. API Gateway only receives webhooks and creates tasks.

### Q: Do MCP servers live inside Agent Container?
**A**: NO. The **MCP client** lives in agent-container. MCP **servers** are separate containers.

### Q: How does Agent Container call MCP tools?
**A**: Via MCP client library connecting to MCP servers via stdio over Docker network.

### Q: Can I use the official GitHub MCP server?
**A**: YES! We use `https://github.com/github/github-mcp-server` built in a Docker container. It provides all GitHub tools including PR comments and reactions.

### Q: Why separate MCP servers instead of bundling in agent?
**A**:
1. **Separation of concerns** - Agents execute tasks, MCP servers handle APIs
2. **Independent scaling** - Scale API clients separately from agents
3. **Type safety** - Strict validation at MCP boundary
4. **Reusability** - Multiple agents can use same MCP servers
5. **Testing** - Mock MCP servers for testing

### Q: What if I want to add a new tool?
**A**: Create a new MCP server or extend existing one:
1. Add tool to `@server.list_tools()`
2. Add implementation to `@server.call_tool()`
3. Deploy as new container or update existing
4. Agents automatically discover new tools

---

## Testing MCP Integration

### Unit Test (Mock MCP)
```python
@pytest.mark.asyncio
async def test_agent_calls_github_mcp():
    # Mock MCP client
    mcp_client = MockMCPClient()
    mcp_client.register_tool("github_post_pr_comment", mock_response)

    # Test agent uses MCP
    agent = PRReviewAgent(mcp_client)
    result = await agent.execute(task)

    assert mcp_client.was_called("github_post_pr_comment")
```

### Integration Test (Real MCP)
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_mcp_flow():
    # Requires docker-compose up
    async with MCPClient(host="github-mcp-server") as client:
        result = await client.call_tool(
            "github_post_pr_comment",
            {"owner": "test", "repo": "test", "pr_number": 1, "comment": "test"}
        )
        assert "Successfully posted" in result[0].text
```

---

## Summary

| Component | Location | Contains | Connects To |
|-----------|----------|----------|-------------|
| **API Gateway** | api-gateway/ | Webhook handlers, Task queue client | Redis, PostgreSQL |
| **GitHub MCP Server** | github-mcp-server/ | GitHub API client, MCP tools | GitHub API |
| **Jira MCP Server** | jira-mcp-server/ | Jira API client, MCP tools | Jira API |
| **Slack MCP Server** | slack-mcp-server/ | Slack API client, MCP tools | Slack API |
| **Sentry MCP Server** | sentry-mcp-server/ | Sentry API client, MCP tools | Sentry API |
| **Agent Container** | agent-container/ | MCP client, CLI runner, Task worker | All MCP servers, Redis |

**Key Principle**: MCP servers are **separate containers** providing **tools** to agents via **stdio protocol**.
