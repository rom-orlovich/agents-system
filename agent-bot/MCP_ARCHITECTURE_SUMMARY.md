# MCP Architecture Summary - Where Do Components Live?

## Your Question Answered

**Q**: "Does the MCP we created live with the client of these services and live inside the container of the API?"

**A**: **NO**. Here's exactly where everything lives:

---

## Component Locations (Simple)

### 1. **API Gateway Container** (`api-gateway/`)
**Lives Here**:
- ✅ Webhook handlers (GitHub, Jira, Slack, Sentry)
- ✅ Signature validators
- ✅ Task queue client (Redis)
- ✅ HTTP server (FastAPI)

**Does NOT Live Here**:
- ❌ MCP servers
- ❌ MCP client
- ❌ External API clients (GitHub API, Jira API, etc.)

**Job**: Receive webhooks → Validate → Create tasks → Put in queue

---

### 2. **MCP Server Containers** (4 separate containers)
**Lives Here**:
- ✅ MCP server implementation (FastMCP)
- ✅ External API clients (httpx)
- ✅ Tool implementations
- ✅ Pydantic models for validation

**Containers**:
1. `github-mcp-server` - Official GitHub MCP (Node.js)
2. `jira-mcp-server` - Custom Jira MCP (Python)
3. `slack-mcp-server` - Custom Slack MCP (Python)
4. `sentry-mcp-server` - Custom Sentry MCP (Python)

**Job**: Provide tools to agents → Call external APIs → Return results

---

### 3. **Agent Container** (`agent-container/`)
**Lives Here**:
- ✅ **MCP Client Library** (connects TO MCP servers)
- ✅ Claude CLI or Cursor CLI
- ✅ Task worker (dequeues from Redis)
- ✅ `.claude/` configuration

**Does NOT Live Here**:
- ❌ MCP server implementations

**Job**: Dequeue tasks → Execute → Use MCP tools → Log results

---

## Visual Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ API GATEWAY CONTAINER                                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │GitHub Handler│  │ Jira Handler │  │Slack Handler │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  - Receives webhooks (HTTP)                                │
│  - Validates signatures                                    │
│  - Creates tasks                                           │
│  - Enqueues to Redis                                       │
│                                                             │
│  ❌ NO MCP servers here!                                   │
│  ❌ NO MCP client here!                                    │
│  ❌ NO external API calls here!                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Task created
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ REDIS QUEUE                                                 │
│  - Stores tasks                                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Task dequeued
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ AGENT CONTAINER                                             │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ MCP CLIENT LIBRARY                                    │ │
│  │ - Connects TO MCP servers                             │ │
│  │ - Lives HERE in agent container                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Task Worker + Claude CLI                              │ │
│  │ - Processes tasks                                      │ │
│  │ - Uses MCP client to call tools                        │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ✅ MCP CLIENT lives here                                  │
│  ❌ MCP SERVERS do NOT live here                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ stdio (calls MCP tools)
                          ↓
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ GITHUB MCP   │  JIRA MCP    │  SLACK MCP   │ SENTRY MCP   │
│ CONTAINER    │  CONTAINER   │  CONTAINER   │  CONTAINER   │
│              │              │              │              │
│ - Server     │ - Server     │ - Server     │ - Server     │
│   code       │   code       │   code       │   code       │
│ - API client │ - API client │ - API client │ - API client │
│ - Tools      │ - Tools      │ - Tools      │ - Tools      │
│              │              │              │              │
│ Separate!    │ Separate!    │ Separate!    │ Separate!    │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘
       │              │              │              │
       │ HTTPS        │ HTTPS        │ HTTPS        │ HTTPS
       ↓              ↓              ↓              ↓
  GitHub API     Jira API      Slack API     Sentry API
```

---

## How It Works (Step by Step)

### 1. Webhook Arrives
```
GitHub sends webhook → API Gateway container → github_handler.py
```
- API Gateway receives HTTP POST
- Validates signature
- Creates task object
- Puts in Redis queue

**MCP servers are NOT involved here!**

---

### 2. Task Gets Processed
```
Agent Container → Dequeues task from Redis
```
- Task worker pulls from queue
- Passes to Claude CLI

---

### 3. Agent Uses MCP Tool
```
Agent Container → MCP Client → GitHub MCP Server → GitHub API
```

**Inside Agent Container**:
```python
# MCP client lives here
from mcp import Client

async with Client(host="github-mcp-server") as client:
    # Call tool on EXTERNAL MCP server
    result = await client.call_tool(
        "github_post_pr_comment",
        {
            "owner": "org",
            "repo": "repo",
            "pr_number": 123,
            "comment": "LGTM!"
        }
    )
```

**In GitHub MCP Server Container** (separate!):
```python
# Server receives tool call
# Validates with Pydantic
# Calls GitHub API
response = await httpx.post("https://api.github.com/...")
# Returns result
```

---

## Key Points

### ✅ MCP Client Lives in Agent Container
The **client library** that CALLS MCP tools lives inside `agent-container/`.

### ✅ MCP Servers Live in Separate Containers
Each MCP **server** (GitHub, Jira, Slack, Sentry) runs in its own container.

### ❌ MCP Servers Do NOT Live in API Gateway
API Gateway only handles webhooks. It does NOT contain MCP servers or make external API calls.

### ✅ Communication is via stdio Over Docker Network
```yaml
# docker-compose.yml
agent-container:
  environment:
    - MCP_GITHUB_HOST=github-mcp-server  # Connect to separate container
  depends_on:
    - github-mcp-server
```

Agent connects to `github-mcp-server` hostname (Docker network).

---

## Why This Architecture?

### Separation of Concerns
- **API Gateway**: Webhooks only
- **MCP Servers**: External APIs only
- **Agent Container**: Task execution only

### Independent Scaling
```yaml
# Scale each independently
agent-container:
  replicas: 5

github-mcp-server:
  replicas: 2
```

### Type Safety at Boundaries
MCP servers validate ALL inputs with Pydantic before calling APIs.

### Easier Testing
Mock MCP servers for testing agents without hitting real APIs.

---

## Official GitHub MCP Server

We now use the **official GitHub MCP server** from:
https://github.com/github/github-mcp-server

**Dockerfile**:
```dockerfile
FROM node:20-slim
RUN git clone https://github.com/github/github-mcp-server.git .
RUN npm install && npm run build
CMD ["node", "dist/index.js"]
```

This provides ALL GitHub tools including:
- PR comments
- PR reactions
- Issue management
- And more!

---

## Summary Table

| Question | Answer |
|----------|--------|
| Where is MCP **client**? | Agent Container ✅ |
| Where are MCP **servers**? | 4 Separate Containers ✅ |
| Is MCP in API Gateway? | NO ❌ |
| Does API Gateway call GitHub API? | NO ❌ |
| Who calls external APIs? | MCP Servers ✅ |
| How do components communicate? | stdio over Docker network ✅ |

---

## Docker Compose Configuration

```yaml
# MCP servers are SEPARATE containers
github-mcp-server:
  build: ./github-mcp-server
  environment:
    - GITHUB_TOKEN=${GITHUB_TOKEN}

jira-mcp-server:
  build: ./jira-mcp-server
  environment:
    - JIRA_EMAIL=${JIRA_EMAIL}
    - JIRA_API_TOKEN=${JIRA_API_TOKEN}

# Agent container CONNECTS to MCP servers
agent-container:
  build: ./agent-container
  environment:
    - MCP_GITHUB_HOST=github-mcp-server  # Hostname!
    - MCP_JIRA_HOST=jira-mcp-server      # Hostname!
  depends_on:
    - github-mcp-server  # Start MCP servers first
    - jira-mcp-server
```

---

## Final Answer

**No, MCP servers do NOT live inside the API Gateway container.**

**MCP servers are separate containers** that provide tools to agents.

**The MCP client lives in the agent-container** and connects to these separate MCP server containers.

**API Gateway only handles webhooks** - it does not contain MCP servers or make external API calls.
