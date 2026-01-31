# Complete Implementation Plan - Agent System

## Overview

This plan outlines the complete implementation of the containerized agent system as defined in `ARCHITECTURE.md`. The system consists of **14 Docker containers** working together to provide a scalable, multi-agent platform.

## Architecture Summary

### Container Breakdown (14 Total)

1. **Agent Engine** (Scalable: 3 replicas) - Ports 8080-8089
2. **GitHub MCP Server** - Port 9001
3. **Jira MCP Server** - Port 9002
4. **Slack MCP Server** - Port 9003
5. **Sentry MCP Server** - Port 9004
6. **GitHub API Service** - Port 3001
7. **Jira API Service** - Port 3002
8. **Slack API Service** - Port 3003
9. **Sentry API Service** - Port 3004
10. **API Gateway** - Port 8000
11. **Internal Dashboard API** - Port 5000
12. **External Dashboard** - Port 3002
13. **Knowledge Graph** (GitLab Rust) - Port 4000
14. **Redis** - Port 6379
15. **PostgreSQL** - Port 5432

## Project Structure (from ARCHITECTURE.md)

```
agents-system/
├── claude.md                        # Global configuration
├── docker-compose.yml               # Main orchestration
├── .env
├── .env.example
├── Makefile
├── README.md
│
├── agent-engine/                    # Agent Engine (Scalable)
│   ├── Dockerfile
│   ├── mcp.json                     # Points to MCP containers
│   ├── claude.md
│   ├── .claude/
│   │   ├── rules/
│   │   ├── skills/
│   │   ├── agents/
│   │   ├── commands/
│   │   └── hooks/
│   ├── core/
│   │   ├── engine.py
│   │   ├── worker.py
│   │   ├── queue_manager.py
│   │   └── cli/                     # CLI Executors
│   │       ├── executor.py          # Main executor (provider-agnostic)
│   │       ├── providers/
│   │       │   ├── claude/          # Claude Code CLI provider
│   │       │   │   ├── __init__.py
│   │       │   │   ├── executor.py
│   │       │   │   └── config.py
│   │       │   └── cursor/          # Cursor CLI provider
│   │       │       ├── __init__.py
│   │       │       ├── executor.py
│   │       │       └── config.py
│   │       └── base.py              # Base provider interface
│   ├── config/
│   │   └── settings.py
│   ├── scripts/
│   │   └── setup_repos.sh
│   └── repos/                       # Pre-cloned repositories
│
├── mcp-servers/                     # MCP Servers (Separate Containers)
│   ├── docker-compose.mcp.yml
│   ├── github-mcp/                  # Official GitHub MCP :9001
│   │   ├── Dockerfile
│   │   └── config.json
│   ├── jira-mcp/                    # Custom Jira MCP :9002
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── jira_mcp.py
│   │   └── requirements.txt
│   ├── slack-mcp/                   # Custom Slack MCP :9003
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── slack_mcp.py
│   │   └── requirements.txt
│   └── sentry-mcp/                  # Custom Sentry MCP :9004
│       ├── Dockerfile
│       ├── main.py
│       ├── sentry_mcp.py
│       └── requirements.txt
│
├── api-services/                    # API Services (Separate Containers)
│   ├── docker-compose.services.yml
│   ├── github-api/                  # GitHub API Service :3001
│   ├── jira-api/                    # Jira API Service :3002
│   ├── slack-api/                   # Slack API Service :3003
│   └── sentry-api/                  # Sentry API Service :3004
│
├── api-gateway/                     # API Gateway :8000
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   ├── routes/
│   │   ├── __init__.py
│   │   └── webhooks.py
│   ├── webhooks/
│   │   ├── __init__.py
│   │   ├── github/
│   │   │   ├── __init__.py
│   │   │   ├── handler.py
│   │   │   ├── validator.py
│   │   │   └── events.py
│   │   ├── jira/
│   │   ├── slack/
│   │   └── sentry/
│   └── middleware/
│       ├── __init__.py
│       ├── auth.py
│       └── error_handler.py
│
├── internal-dashboard-api/          # Internal Dashboard API :5000
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── agents.py
│   │   │   ├── tasks.py
│   │   │   ├── monitoring.py
│   │   │   └── metrics.py
│   │   └── server.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent_manager.py
│   │   ├── task_manager.py
│   │   └── metrics_collector.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   └── middleware/
│       ├── __init__.py
│       ├── auth.py
│       └── error_handler.py
│
├── external-dashboard/              # External Dashboard :3002
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── static/
│   │   ├── templates/
│   │   └── routes.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── client.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   └── storage/
│       ├── __init__.py
│       └── session.py
│
├── knowledge-graph/                 # Knowledge Graph :4000
│   ├── Dockerfile
│   ├── config/
│   ├── api/
│   └── engine/
│
└── docs/
    └── CONTAINERIZED-AGENT-ARCHITECTURE.md
```

## Implementation Phases

### Phase 1: Infrastructure Setup ✅ (Week 1)
**Status**: COMPLETE

- [x] Docker network creation
- [x] Redis container
- [x] PostgreSQL container
- [x] Basic docker-compose.yml

### Phase 2: API Services Layer ✅ (Week 2)
**Status**: COMPLETE

- [x] GitHub API Service (port 3001)
- [x] Jira API Service (port 3002)
- [x] Slack API Service (port 3003)
- [x] Sentry API Service (port 3004)
- [x] docker-compose.services.yml

### Phase 3: MCP Servers ✅ (Week 3-4)
**Status**: COMPLETE

#### 3.1 Official GitHub MCP Server
- [x] Create `mcp-servers/github-mcp/Dockerfile`
- [x] Set up SSE transport on port 9001
- [x] Add health checks

#### 3.2 Custom Jira MCP Server
- [x] Create `mcp-servers/jira-mcp/` structure
- [x] Implement with FastMCP (7 tools)
- [x] Set up SSE transport on port 9002
- [x] Connect to jira-api:3002

#### 3.3 Custom Slack MCP Server
- [x] Create `mcp-servers/slack-mcp/` structure
- [x] Implement with FastMCP (8 tools)
- [x] Set up SSE transport on port 9003
- [x] Connect to slack-api:3003

#### 3.4 Custom Sentry MCP Server
- [x] Create `mcp-servers/sentry-mcp/` structure
- [x] Implement with FastMCP (10 tools)
- [x] Set up SSE transport on port 9004
- [x] Connect to sentry-api:3004

#### 3.5 MCP Docker Compose
- [x] Create `mcp-servers/docker-compose.mcp.yml`
- [x] Configure all 4 MCP servers
- [x] Add health checks
- [x] Set up networking

### Phase 4: Agent Engine Core ✅ (Week 5-6)
**Status**: COMPLETE

#### 4.1 Agent Engine Container
- [x] Create `agent-engine/main.py` with task worker
- [x] Implement CLI provider support (Claude/Cursor)
- [x] Add configuration settings

#### 4.2 Task Worker & Queue Manager
- [x] Implement Redis queue consumer
- [x] Add task execution loop
- [x] Add task status updates via Redis pub/sub

#### 4.3 Agent Definitions
- [x] Create `.claude/` directory structure
- [x] Create 9 agent definitions (brain, planning, executor, etc.)
- [x] Create mcp.json configuration

#### 4.4 Agent Engine Configuration
- [x] Create Dockerfile
- [x] Configure for scalability (3 replicas)
- [x] Add environment variables
- [x] Create docker-compose.agent.yml

### Phase 5: API Gateway Webhooks ✅ (Week 7)
**Status**: COMPLETE

#### 5.1 GitHub Webhooks
- [x] Create `api-gateway/webhooks/github/handler.py`
- [x] Create `api-gateway/webhooks/github/validator.py`
- [x] Create `api-gateway/webhooks/github/events.py`
- [x] Implement HMAC signature validation
- [x] Add event routing logic

#### 5.2 Jira Webhooks
- [x] Create `api-gateway/webhooks/jira/` structure
- [x] Implement handler, validator, events
- [x] Add AI-Fix label filtering

#### 5.3 Slack Webhooks
- [x] Create `api-gateway/webhooks/slack/` structure
- [x] Implement handler, validator, events
- [x] Add Slack signature validation with timestamp check
- [x] Handle URL verification challenge

#### 5.4 Sentry Webhooks
- [x] Create `api-gateway/webhooks/sentry/` structure
- [x] Implement handler, validator, events
- [x] Add Sentry-specific validation

#### 5.5 Webhook Middleware & Main App
- [x] Create auth middleware
- [x] Create error handling middleware
- [x] Create main.py with all routes registered

### Phase 6: Dashboard Layer ✅ (Week 8-9)
**Status**: COMPLETE

#### 6.1 Internal Dashboard API
- [x] Create API routes (agents, tasks, monitoring, metrics)
- [x] Implement services (agent_manager, task_manager, metrics_collector)
- [x] Add WebSocket support for real-time task updates
- [x] Add Prometheus metrics endpoint
- [x] Add middleware

#### 6.2 External Dashboard
- [ ] Create React dashboard (PENDING - low priority)

### Phase 7: Knowledge Graph 📋 (Week 10)
**Status**: PLANNED

- [ ] Set up Rust development environment
- [ ] Implement graph storage
- [ ] Create API endpoints
- [ ] Add entity extraction
- [ ] Implement relationship management

### Phase 8: Integration & Testing 📋 (Week 11-12)
**Status**: PLANNED

#### 8.1 Docker Compose Integration
- [ ] Update main docker-compose.yml
- [ ] Add all 14 containers
- [ ] Configure networking
- [ ] Add health checks
- [ ] Set up startup order

#### 8.2 End-to-End Testing
- [ ] Test webhook → task creation → execution flow
- [ ] Test dashboard → agent engine communication
- [ ] Test MCP server connections
- [ ] Load testing (100+ concurrent tasks)
- [ ] Fix integration issues

#### 8.3 Production Readiness
- [ ] Security audit (Trivy, Snyk)
- [ ] Monitoring setup (Prometheus, Grafana)
- [ ] Backup/recovery procedures
- [ ] Documentation finalization
- [ ] Deployment guides

## Migration from claude-code-agent

### Key Files to Migrate

| Source (claude-code-agent) | Destination | Notes |
|----------------------------|-------------|-------|
| `core/cli_runner.py` | `agent-engine/core/cli/providers/claude/executor.py` | Split into provider |
| `workers/task_worker.py` | `agent-engine/core/worker.py` | Simplified |
| `core/config.py` | `internal-dashboard-api/config/settings.py` | Pydantic settings |
| `shared/machine_models.py` | Shared package models | Extend existing |
| `api/webhooks/github/` | `api-gateway/webhooks/github/` | Adapt to new arch |
| `api/webhooks/jira/` | `api-gateway/webhooks/jira/` | Adapt to new arch |
| `api/webhooks/slack/` | `api-gateway/webhooks/slack/` | Adapt to new arch |
| `api/dashboard.py` | `internal-dashboard-api/api/routes/` | Split by domain |
| `api/conversations.py` | `internal-dashboard-api/api/routes/conversations.py` | Direct copy |
| `api/websocket.py` | `internal-dashboard-api/api/routes/websocket.py` | Direct copy |
| `.claude/CLAUDE.md` | `agent-engine/.claude/CLAUDE.md` | Direct copy |
| `.claude/agents/*.md` | `agent-engine/.claude/agents/*.md` | Direct copy |
| `.claude/skills/*` | `agent-engine/.claude/skills/*` | Direct copy |
| `services/dashboard-v2/src/*` | `external-dashboard/src/*` | Direct copy |

## Timeline

- **Week 1-2**: ✅ Infrastructure + API Services (COMPLETE)
- **Week 3-4**: ✅ MCP Servers (COMPLETE)
- **Week 5-6**: ✅ Agent Engine Core (COMPLETE)
- **Week 7**: ✅ API Gateway Webhooks (COMPLETE)
- **Week 8-9**: ✅ Dashboard Layer (COMPLETE)
- **Week 10**: 📋 Knowledge Graph (PENDING)
- **Week 11-12**: 📋 Integration & Testing (PENDING)

**Total Estimated Duration**: 12 weeks
**Current Progress**: 6 of 8 phases complete (~75%)

## Success Criteria

- [ ] All 14 containers running successfully
- [ ] Webhooks receiving and processing events
- [ ] Tasks executing via Claude CLI
- [ ] Dashboard showing real-time updates
- [ ] Conversations persisting correctly
- [ ] Analytics working
- [ ] All tests passing (unit, integration, E2E)
- [ ] Documentation complete
- [ ] Production deployment successful

## Next Immediate Steps

1. **Complete MCP Servers** (Phase 3)
   - Start with GitHub MCP (official)
   - Build custom MCP servers for Jira, Slack, Sentry
   - Test SSE connections

2. **Start Agent Engine** (Phase 4)
   - Implement CLI provider architecture
   - Create task worker and queue manager
   - Migrate agent definitions

3. **Implement Webhooks** (Phase 5)
   - Build webhook handlers
   - Add validation
   - Connect to Redis queue

---

**Created**: 2026-01-31
**Last Updated**: 2026-01-31
**Status**: Phases 1-6 Complete, Phase 7 (Knowledge Graph) and Phase 8 (Integration) Pending
**Next Milestone**: Knowledge Graph implementation or Integration Testing
