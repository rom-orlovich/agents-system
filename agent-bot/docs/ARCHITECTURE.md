# Agent Bot Architecture

## Overview

A fully containerized, scalable multi-agent system where **each service runs in its own Docker container** for maximum isolation, scalability, and maintainability. The system processes webhooks from GitHub, Jira, Slack, and Sentry to autonomously handle development tasks.

---

## Container Architecture

### Total Services: 18

| #   | Service                 | Port      | Purpose                     |
| --- | ----------------------- | --------- | --------------------------- |
| 1   | **CLI (Agent Engine)**  | 8080-8089 | Task execution (scalable)   |
| 2   | **API Gateway**         | 8000      | Webhook reception           |
| 3   | **Dashboard API**       | 5000      | Analytics & WebSocket hub   |
| 4   | **External Dashboard**  | 3005      | React monitoring UI         |
| 5   | **OAuth Service**       | 8010      | Multi-provider OAuth flows  |
| 6   | **Task Logger**         | 8090      | Task output logging         |
| 7   | **Knowledge Graph**     | 4000      | Code entity indexing (Rust) |
| 8   | **GitHub MCP**          | 9001      | GitHub tool interface       |
| 9   | **Jira MCP**            | 9002      | Jira tool interface         |
| 10  | **Slack MCP**           | 9003      | Slack tool interface        |
| 11  | **Sentry MCP**          | 9004      | Sentry tool interface       |
| 12  | **Knowledge Graph MCP** | 9005      | Code search tool interface  |
| 13  | **GitHub API**          | 3001      | GitHub API wrapper          |
| 14  | **Jira API**            | 3002      | Jira API wrapper            |
| 15  | **Slack API**           | 3003      | Slack API wrapper           |
| 16  | **Sentry API**          | 3004      | Sentry API wrapper          |
| 17  | **Redis**               | 6379      | Task queue & cache          |
| 18  | **PostgreSQL**          | 5432      | Persistent storage          |

---

## System Diagram

```mermaid
graph TB
    subgraph External["External Services"]
        GitHub[GitHub]
        Jira[Jira]
        Slack[Slack]
        Sentry[Sentry]
    end

    subgraph Gateway["API Gateway :8000"]
        Webhooks["GitHub Webhook<br/>Jira Webhook<br/>Slack Webhook<br/>Sentry Webhook"]
    end

    subgraph Storage["Storage Layer"]
        Redis[Redis :6379]
        Postgres[PostgreSQL :5432]
    end

    subgraph Engine["CLI Agent Engine :8080-8089"]
        Agents[".claude/agents/<br/>brain, planning, executor<br/>github-issue-handler<br/>github-pr-review<br/>jira-code-plan<br/>slack-inquiry, verifier<br/>(Supports Claude & Cursor)"]
        MCPConn["MCP Connections SSE"]
    end

    subgraph MCPServers["MCP Servers"]
        GitHubMCP[GitHub MCP :9001]
        JiraMCP[Jira MCP :9002]
        SlackMCP[Slack MCP :9003]
        SentryMCP[Sentry MCP :9004]
        KGMCP[Knowledge Graph MCP :9005]
    end

    subgraph APIServices["API Services"]
        GitHubAPI[GitHub API :3001<br/>Token]
        JiraAPI[Jira API :3002<br/>API Key]
        SlackAPI[Slack API :3003<br/>Token]
        SentryAPI[Sentry API :3004<br/>DSN]
    end

    subgraph Monitoring["Monitoring & Management"]
        DashboardAPI[Dashboard API :5000<br/>WebSocket, Analytics]
        ExternalDash[External Dashboard :3005<br/>React UI]
        OAuth[OAuth Service :8010<br/>GitHub, Slack, Jira]
        TaskLogger[Task Logger :8090<br/>Redis Pub/Sub, File logging]
    end

    External -->|Webhooks| Gateway
    Gateway --> Webhooks
    Webhooks --> Redis
    Webhooks --> Postgres
    Redis --> Engine
    Postgres --> Engine
    Engine --> Agents
    Engine --> MCPConn
    MCPConn -->|SSE| MCPServers
    MCPServers --> GitHubMCP
    MCPServers --> JiraMCP
    MCPServers --> SlackMCP
    MCPServers --> SentryMCP
    MCPServers --> KGMCP
    GitHubMCP -->|HTTP| GitHubAPI
    JiraMCP -->|HTTP| JiraAPI
    SlackMCP -->|HTTP| SlackAPI
    SentryMCP -->|HTTP| SentryAPI
    GitHubAPI --> GitHub
    JiraAPI --> Jira
    SlackAPI --> Slack
    SentryAPI --> Sentry
    Engine --> DashboardAPI
    DashboardAPI -->|WebSocket| ExternalDash
    Engine --> TaskLogger
    Engine --> OAuth
```

---

## Data Flow

### Task Lifecycle

```mermaid
flowchart TD
    A[External Event<br/>GitHub, Jira, Slack, Sentry] --> B[Webhook → api-gateway:8000]
    B --> C[Validate signature + extract metadata]
    C --> D[Create task in PostgreSQL]
    D --> E[Enqueue to Redis<br/>agent:tasks queue]
    E --> F[CLI agent-engine:8080<br/>picks up task BRPOP]
    F --> G[Update status:<br/>QUEUED → RUNNING]
    G --> H[Execute CLI provider<br/>claude or cursor]
    H --> I[Stream output to<br/>Redis Pub/Sub]
    I --> J[task-logger:8090<br/>captures output to files]
    I --> K[dashboard-api:5000<br/>broadcasts via WebSocket]
    H --> L[Agent calls MCP tools<br/>as needed]
    L --> M[Post response back<br/>to source system]
    M --> N[Update status:<br/>RUNNING → COMPLETED/FAILED]
```

### Task Status State Machine

```mermaid
stateDiagram-v2
    [*] --> QUEUED
    QUEUED --> RUNNING
    QUEUED --> CANCELLED
    RUNNING --> WAITING_INPUT
    RUNNING --> COMPLETED
    RUNNING --> FAILED
    RUNNING --> CANCELLED
    WAITING_INPUT --> RUNNING
    WAITING_INPUT --> CANCELLED
    COMPLETED --> [*]
    FAILED --> [*]
    CANCELLED --> [*]
```

**Valid Transitions:**

- `QUEUED` → `RUNNING`, `CANCELLED`
- `RUNNING` → `WAITING_INPUT`, `COMPLETED`, `FAILED`, `CANCELLED`
- `WAITING_INPUT` → `RUNNING`, `CANCELLED`
- Terminal states (`COMPLETED`, `FAILED`, `CANCELLED`) cannot transition

---

## Project Structure

```
agent-bot/
├── CLAUDE.md                           # Project-level rules
├── docker-compose.yml                  # Main orchestration
├── Makefile                            # Development commands
├── .env.example
│
├── agent-engine/                       # CLI Task Execution (Scalable)
│   ├── Dockerfile
│   ├── main.py                         # FastAPI + Redis worker
│   ├── .claude/
│   │   ├── agents/                     # 13 specialized agents
│   │   │   ├── brain.md                # Main orchestrator
│   │   │   ├── planning.md             # Discovery & planning
│   │   │   ├── executor.md             # TDD implementation
│   │   │   ├── verifier.md             # Quality assurance
│   │   │   ├── github-issue-handler.md # Issue processing
│   │   │   ├── github-pr-review.md     # PR review
│   │   │   ├── jira-code-plan.md       # Jira ticket handling
│   │   │   ├── slack-inquiry.md        # Slack Q&A
│   │   │   └── service-integrator.md   # External coordination
│   │   └── skills/                     # 9 reusable skills
│   │       ├── discovery/              # Repo identification
│   │       ├── testing/                # Test generation
│   │       ├── code-refactoring/       # Code improvements
│   │       ├── github-operations/      # Git/GitHub actions
│   │       ├── jira-operations/        # Jira actions
│   │       ├── slack-operations/       # Slack messaging
│   │       ├── human-approval/         # Approval workflows
│   │       ├── verification/           # Quality checks
│   │       └── knowledge-graph/        # Code search
│   ├── core/
│   │   ├── worker.py                   # Task consumption
│   │   └── cli/
│   │       ├── base.py                 # Provider interface
│   │       ├── factory.py              # Provider factory
│   │       └── providers/
│   │           ├── claude.py           # Claude Code CLI
│   │           └── cursor.py           # Cursor CLI
│   └── config/
│       └── settings.py
│
├── api-gateway/                        # Webhook Reception :8000
│   ├── Dockerfile
│   ├── main.py
│   ├── routes/
│   │   └── webhooks.py
│   └── webhooks/
│       ├── github/
│       │   ├── handler.py
│       │   ├── validator.py
│       │   └── events.py
│       ├── jira/
│       ├── slack/
│       └── sentry/
│
├── dashboard-api/                      # Analytics & WebSocket :5000
│   ├── Dockerfile
│   ├── main.py
│   ├── api/
│   │   ├── analytics.py
│   │   ├── conversations.py
│   │   ├── dashboard.py
│   │   ├── webhook_status.py
│   │   └── websocket.py
│   └── core/
│       ├── database/
│       │   ├── models.py
│       │   └── redis_client.py
│       └── websocket_hub.py
│
├── external-dashboard/                 # React UI :3005
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── features/
│       │   ├── overview/
│       │   ├── analytics/
│       │   ├── ledger/
│       │   ├── webhooks/
│       │   ├── chat/
│       │   └── registry/
│       └── hooks/
│           ├── useWebSocket.ts
│           └── useCLIStatus.ts
│
├── oauth-service/                      # OAuth Flows :8010
│   ├── Dockerfile
│   ├── main.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── github.py
│   │   ├── jira.py
│   │   └── slack.py
│   └── services/
│       ├── installation_service.py
│       └── token_service.py
│
├── task-logger/                        # Task Output Logging :8090
│   ├── Dockerfile
│   ├── main.py
│   └── core/
│       └── log_writer.py
│
├── mcp-servers/                        # MCP Protocol Servers
│   ├── github-mcp/       :9001         # Official GitHub MCP
│   ├── jira-mcp/         :9002         # FastMCP - Jira
│   ├── slack-mcp/        :9003         # FastMCP - Slack
│   ├── sentry-mcp/       :9004         # FastMCP - Sentry
│   └── knowledge-graph-mcp/ :9005      # FastMCP - Code Search
│
├── api-services/                       # API Wrappers (Credentials Here)
│   ├── github-api/       :3001
│   ├── jira-api/         :3002
│   ├── slack-api/        :3003
│   └── sentry-api/       :3004
│
├── knowledge-graph/                    # Code Graph Database :4000
│   ├── Dockerfile                      # Rust-based
│   ├── Cargo.toml
│   └── src/
│
└── docs/
    ├── ARCHITECTURE.md                 # This file
    └── BUSINESS-LOGIC-TESTING.md       # Testing guide
```

---

## Port Reference

| Service             | Port(s)   | Container Name      | Purpose                   |
| ------------------- | --------- | ------------------- | ------------------------- |
| CLI (Agent Engine)  | 8080-8089 | cli                 | Task execution (scalable) |
| API Gateway         | 8000      | api-gateway         | Webhook reception         |
| Dashboard API       | 5000      | dashboard-api       | Analytics & WebSocket     |
| External Dashboard  | 3005      | external-dashboard  | React monitoring UI       |
| OAuth Service       | 8010      | oauth-service       | Multi-provider OAuth      |
| Task Logger         | 8090      | task-logger         | Output logging            |
| Knowledge Graph     | 4000      | knowledge-graph     | Code entity indexing      |
| GitHub MCP          | 9001      | github-mcp          | GitHub tool interface     |
| Jira MCP            | 9002      | jira-mcp            | Jira tool interface       |
| Slack MCP           | 9003      | slack-mcp           | Slack tool interface      |
| Sentry MCP          | 9004      | sentry-mcp          | Sentry tool interface     |
| Knowledge Graph MCP | 9005      | knowledge-graph-mcp | Code search interface     |
| GitHub API          | 3001      | github-api          | GitHub API wrapper        |
| Jira API            | 3002      | jira-api            | Jira API wrapper          |
| Slack API           | 3003      | slack-api           | Slack API wrapper         |
| Sentry API          | 3004      | sentry-api          | Sentry API wrapper        |
| Redis               | 6379      | redis               | Task queue & cache        |
| PostgreSQL          | 5432      | postgres            | Persistent storage        |

---

## Agent Architecture

### Specialized Agents

| Agent                    | Trigger Source   | Purpose                                 |
| ------------------------ | ---------------- | --------------------------------------- |
| **brain**                | Internal routing | Main orchestrator, task decomposition   |
| **planning**             | Discovery tasks  | Code discovery, implementation planning |
| **executor**             | Implementation   | TDD-based code implementation           |
| **verifier**             | Quality checks   | Code review, test verification          |
| **github-issue-handler** | GitHub issues    | Issue analysis and response             |
| **github-pr-review**     | GitHub PRs       | PR review and feedback                  |
| **jira-code-plan**       | Jira tickets     | AI-Fix ticket processing                |
| **slack-inquiry**        | Slack mentions   | Q&A and command handling                |
| **service-integrator**   | Cross-service    | External service coordination           |

### Agent Routing

| Source    | Event Type              | Target Agent         |
| --------- | ----------------------- | -------------------- |
| GitHub    | Issue opened/commented  | github-issue-handler |
| GitHub    | PR opened/reviewed      | github-pr-review     |
| Jira      | Issue with AI-Fix label | jira-code-plan       |
| Slack     | @agent mention          | slack-inquiry        |
| Sentry    | Error alert             | planning → executor  |
| Dashboard | Discovery request       | planning             |
| Dashboard | Implementation          | executor             |

### CLI Provider Selection

```python
COMPLEX_AGENTS = ["planning", "consultation", "question_asking", "brain"]
# → Uses Opus (Claude) or Pro model (Cursor)

EXECUTION_AGENTS = ["executor", "github-issue-handler", "jira-code-plan"]
# → Uses Sonnet (Claude) or Standard model (Cursor)
```

---

## MCP Configuration

**agent-engine/.claude/mcp.json:**

```json
{
  "mcpServers": {
    "github": {
      "url": "http://github-mcp:9001/sse",
      "transport": "sse"
    },
    "jira": {
      "url": "http://jira-mcp:9002/sse",
      "transport": "sse"
    },
    "slack": {
      "url": "http://slack-mcp:9003/sse",
      "transport": "sse"
    },
    "sentry": {
      "url": "http://sentry-mcp:9004/sse",
      "transport": "sse"
    },
    "knowledge-graph": {
      "url": "http://knowledge-graph-mcp:9005/sse",
      "transport": "sse"
    }
  }
}
```

### MCP Tools by Server

| Server              | Tools                                                                               |
| ------------------- | ----------------------------------------------------------------------------------- |
| github-mcp          | create_pull_request, get_file_contents, create_branch, add_comment, search_code     |
| jira-mcp            | get_issue, create_issue, update_issue, add_comment, search_issues, transition_issue |
| slack-mcp           | post_message, get_conversations, list_channels, reply_in_thread                     |
| sentry-mcp          | get_issue, add_comment, update_status, get_events                                   |
| knowledge-graph-mcp | search_code, find_references, get_call_graph, get_dependencies                      |

---

## Security Model

### Credential Isolation

```mermaid
graph TB
    subgraph CredentialFree["CREDENTIAL-FREE ZONE"]
        APIGateway[API Gateway :8000<br/>No API keys]
        MCPServers[MCP Servers :9001-9005<br/>No API keys]
        CLI[CLI Agent Engine :8080-8089<br/>No API keys]
    end

    subgraph APIServicesZone["API SERVICES (Keys Here)"]
        GitHubAPI[GitHub API :3001<br/>GITHUB_TOKEN]
        JiraAPI[Jira API :3002<br/>JIRA_API_KEY]
        SlackAPI[Slack API :3003<br/>SLACK_BOT_TOKEN]
        SentryAPI[Sentry API :3004<br/>SENTRY_DSN]
    end

    CredentialFree -->|HTTP only| APIServicesZone
    APIGateway -.->|No credentials| MCPServers
    MCPServers -.->|No credentials| CLI
    CLI -.->|No credentials| MCPServers
```

### Webhook Signature Validation

- GitHub: HMAC-SHA256 (`X-Hub-Signature-256`)
- Jira: HMAC-SHA256 (`X-Atlassian-Webhook-Signature`)
- Slack: HMAC-SHA256 (`X-Slack-Signature`)
- Sentry: Token-based (`Sentry-Hook-Signature`)

### Loop Prevention

Agent-posted comments are tracked in Redis to prevent infinite webhook loops:

```
Key: posted_comments:{comment_id}
TTL: 1 hour
Check: Before processing webhook, verify comment_id not in Redis
```

---

## Environment Variables

### Infrastructure

```bash
POSTGRES_PASSWORD=agent
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_system
```

### CLI Provider

```bash
CLI_PROVIDER=claude                    # or 'cursor'
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT_SECONDS=3600
ANTHROPIC_API_KEY=sk-ant-xxx
CURSOR_API_KEY=xxx
```

### External Services

```bash
GITHUB_TOKEN=ghp_xxx
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=xxx
SLACK_BOT_TOKEN=xoxb-xxx
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_AUTH_TOKEN=xxx
```

### Webhook Secrets

```bash
GITHUB_WEBHOOK_SECRET=xxx
JIRA_WEBHOOK_SECRET=xxx
SLACK_WEBHOOK_SECRET=xxx
```

### OAuth (Optional)

```bash
OAUTH_BASE_URL=http://localhost:8010
GITHUB_APP_ID=xxx
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
SLACK_CLIENT_ID=xxx
SLACK_CLIENT_SECRET=xxx
JIRA_CLIENT_ID=xxx
JIRA_CLIENT_SECRET=xxx
TOKEN_ENCRYPTION_KEY=xxx
```

---

## Deployment

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 2. Start all services
make init
make cli-up PROVIDER=claude SCALE=1

# 3. Verify health
make cli-status PROVIDER=claude
curl http://localhost:8000/health
```

### Scaling

```bash
# Scale CLI workers
make cli-up PROVIDER=claude SCALE=3

# Scale specific service
docker-compose up -d --scale cli=5 cli
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f cli
docker-compose logs -f api-gateway
docker-compose logs -f dashboard-api

# Task execution logs
docker-compose logs -f task-logger
```

### Health Checks

```bash
curl http://localhost:8000/health      # API Gateway
curl http://localhost:8080/health      # CLI (Agent Engine)
curl http://localhost:5000/health      # Dashboard API
curl http://localhost:8010/health      # OAuth Service
curl http://localhost:8090/health      # Task Logger
curl http://localhost:4000/health      # Knowledge Graph
```

---

## Key Benefits

### 1. Maximum Isolation

- Each service in own container
- Failure in one doesn't affect others
- Easy to debug and monitor

### 2. Independent Scaling

- Scale CLI workers horizontally (1-N instances)
- Scale each MCP server independently
- Scale each API service independently

### 3. Security

- API keys only in API service containers
- No keys in MCP servers, webhooks, or agents
- Webhook signature validation
- Loop prevention for agent-posted content

### 4. Maintainability

- Update one service without affecting others
- Clear boundaries and responsibilities
- Easy to add new services or agents

### 5. Observability

- Real-time WebSocket updates
- Task output logging
- Analytics and metrics dashboard
- Structured logging throughout

---

## Related Documentation

- [BUSINESS-LOGIC-TESTING.md](./BUSINESS-LOGIC-TESTING.md) - Testing strategy for business logic
- [CLAUDE.md](../CLAUDE.md) - Development rules and conventions
