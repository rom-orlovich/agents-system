# Implementation Tasks - Detailed Breakdown

## Current Status

- ✅ **Phase 1**: Infrastructure (Redis, PostgreSQL, Docker network)
- ✅ **Phase 2**: API Services (4 services on ports 3001-3004)
- 🚧 **Phase 3**: MCP Servers (NEXT - Starting now)
- 📋 **Phase 4**: Agent Engine
- 📋 **Phase 5**: API Gateway Webhooks
- 📋 **Phase 6**: Dashboard Layer
- 📋 **Phase 7**: Knowledge Graph
- 📋 **Phase 8**: Integration & Testing

## Phase 3: MCP Servers (CURRENT FOCUS)

### Task 3.1: GitHub MCP Server (Official)
**Priority**: HIGH
**Duration**: 2 days
**Dependencies**: API Services (Phase 2)

#### Subtasks:
1. [ ] Create `mcp-servers/github-mcp/` directory
2. [ ] Create Dockerfile using official GitHub MCP image
3. [ ] Create config.json for GitHub MCP configuration
4. [ ] Configure SSE transport on port 9001
5. [ ] Set environment variable for github-api URL
6. [ ] Add health check endpoint
7. [ ] Test connection to github-api:3001
8. [ ] Test SSE connection from agent engine

**Files to Create**:
- `mcp-servers/github-mcp/Dockerfile`
- `mcp-servers/github-mcp/.env.example`

**Example Dockerfile**:
```dockerfile
FROM node:20-alpine

WORKDIR /app

# Install git and build dependencies
RUN apk add --no-cache git

# Clone official GitHub MCP server
RUN git clone https://github.com/github/github-mcp-server.git . && \
    npm install && \
    npm run build

# Expose SSE port
EXPOSE 9001

# Environment variables will be passed from docker-compose
ENV PORT=9001

# Start server with SSE transport
CMD ["node", "dist/index.js"]
```

**Note**: The official GitHub MCP server (https://github.com/github/github-mcp-server) doesn't have a pre-built Docker image, so we build from source. The server will connect to our `github-api:3001` service for actual GitHub API calls.

### Task 3.2: Jira MCP Server (Custom with FastMCP)
**Priority**: HIGH
**Duration**: 2 days
**Dependencies**: API Services (Phase 2)

#### Subtasks:
1. [ ] Create `mcp-servers/jira-mcp/` directory
2. [ ] Create Dockerfile with Python 3.11
3. [ ] Create requirements.txt (fastmcp, httpx, pydantic)
4. [ ] Create main.py with FastMCP server
5. [ ] Create jira_mcp.py with Jira tools
6. [ ] Implement tools:
   - [ ] `get_issue` - Get Jira issue details
   - [ ] `create_issue` - Create new issue
   - [ ] `update_issue` - Update issue
   - [ ] `add_comment` - Add comment to issue
   - [ ] `search_issues` - Search issues with JQL
7. [ ] Configure SSE transport on port 9002
8. [ ] Connect to jira-api:3002
9. [ ] Add health check
10. [ ] Test all tools

**Files to Create**:
- `mcp-servers/jira-mcp/Dockerfile`
- `mcp-servers/jira-mcp/main.py`
- `mcp-servers/jira-mcp/jira_mcp.py`
- `mcp-servers/jira-mcp/requirements.txt`
- `mcp-servers/jira-mcp/.env.example`

**Example main.py**:
```python
from fastmcp import FastMCP
from jira_mcp import JiraMCP

mcp = FastMCP("Jira MCP Server")
jira = JiraMCP(api_url="http://jira-api:3002")

@mcp.tool()
async def get_issue(issue_key: str) -> dict:
    """Get Jira issue details"""
    return await jira.get_issue(issue_key)

@mcp.tool()
async def create_issue(project: str, summary: str, description: str) -> dict:
    """Create new Jira issue"""
    return await jira.create_issue(project, summary, description)

# ... more tools

if __name__ == "__main__":
    mcp.run(transport="sse", port=9002)
```

### Task 3.3: Slack MCP Server (Custom with FastMCP)
**Priority**: HIGH
**Duration**: 2 days
**Dependencies**: API Services (Phase 2)

#### Subtasks:
1. [ ] Create `mcp-servers/slack-mcp/` directory
2. [ ] Create Dockerfile with Python 3.11
3. [ ] Create requirements.txt (fastmcp, httpx, pydantic)
4. [ ] Create main.py with FastMCP server
5. [ ] Create slack_mcp.py with Slack tools
6. [ ] Implement tools:
   - [ ] `send_message` - Send message to channel
   - [ ] `get_channel_history` - Get channel messages
   - [ ] `get_thread` - Get thread messages
   - [ ] `add_reaction` - Add reaction to message
   - [ ] `upload_file` - Upload file to channel
7. [ ] Configure SSE transport on port 9003
8. [ ] Connect to slack-api:3003
9. [ ] Add health check
10. [ ] Test all tools

**Files to Create**:
- `mcp-servers/slack-mcp/Dockerfile`
- `mcp-servers/slack-mcp/main.py`
- `mcp-servers/slack-mcp/slack_mcp.py`
- `mcp-servers/slack-mcp/requirements.txt`
- `mcp-servers/slack-mcp/.env.example`

### Task 3.4: Sentry MCP Server (Custom with FastMCP)
**Priority**: MEDIUM
**Duration**: 1 day
**Dependencies**: API Services (Phase 2)

#### Subtasks:
1. [ ] Create `mcp-servers/sentry-mcp/` directory
2. [ ] Create Dockerfile with Python 3.11
3. [ ] Create requirements.txt (fastmcp, httpx, pydantic)
4. [ ] Create main.py with FastMCP server
5. [ ] Create sentry_mcp.py with Sentry tools
6. [ ] Implement tools:
   - [ ] `get_issues` - Get Sentry issues
   - [ ] `get_issue_details` - Get issue details
   - [ ] `resolve_issue` - Resolve issue
   - [ ] `add_comment` - Add comment to issue
7. [ ] Configure SSE transport on port 9004
8. [ ] Connect to sentry-api:3004
9. [ ] Add health check
10. [ ] Test all tools

**Files to Create**:
- `mcp-servers/sentry-mcp/Dockerfile`
- `mcp-servers/sentry-mcp/main.py`
- `mcp-servers/sentry-mcp/sentry_mcp.py`
- `mcp-servers/sentry-mcp/requirements.txt`
- `mcp-servers/sentry-mcp/.env.example`

### Task 3.5: MCP Docker Compose
**Priority**: HIGH
**Duration**: 1 day
**Dependencies**: Tasks 3.1-3.4

#### Subtasks:
1. [ ] Create `mcp-servers/docker-compose.mcp.yml`
2. [ ] Add github-mcp service
3. [ ] Add jira-mcp service
4. [ ] Add slack-mcp service
5. [ ] Add sentry-mcp service
6. [ ] Configure external network (agent-network)
7. [ ] Add health checks for all services
8. [ ] Add restart policies
9. [ ] Test all services start correctly
10. [ ] Test network connectivity

**File to Create**:
- `mcp-servers/docker-compose.mcp.yml`

**Example docker-compose.mcp.yml**:
```yaml
version: '3.8'

services:
  github-mcp:
    build: ./github-mcp
    container_name: github-mcp
    ports:
      - "9001:9001"
    environment:
      - PORT=9001
      - GITHUB_API_URL=http://github-api:3001
    networks:
      - agent-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  jira-mcp:
    build: ./jira-mcp
    container_name: jira-mcp
    ports:
      - "9002:9002"
    environment:
      - PORT=9002
      - JIRA_API_URL=http://jira-api:3002
    networks:
      - agent-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  slack-mcp:
    build: ./slack-mcp
    container_name: slack-mcp
    ports:
      - "9003:9003"
    environment:
      - PORT=9003
      - SLACK_API_URL=http://slack-api:3003
    networks:
      - agent-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9003/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  sentry-mcp:
    build: ./sentry-mcp
    container_name: sentry-mcp
    ports:
      - "9004:9004"
    environment:
      - PORT=9004
      - SENTRY_API_URL=http://sentry-api:3004
    networks:
      - agent-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9004/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  agent-network:
    external: true
```

## Phase 4: Agent Engine Core (NEXT AFTER PHASE 3)

### Task 4.1: CLI Provider Architecture
**Priority**: CRITICAL
**Duration**: 3 days
**Dependencies**: None

#### Subtasks:
1. [ ] Create `agent-engine/core/cli/` directory
2. [ ] Create `base.py` with BaseCLIProvider interface
3. [ ] Create `executor.py` with main CLIExecutor
4. [ ] Create `providers/claude/` directory
5. [ ] Implement Claude provider executor
6. [ ] Create `providers/claude/config.py`
7. [ ] Create `providers/cursor/` directory (stub)
8. [ ] Add provider loading logic
9. [ ] Add environment variable support (CLI_PROVIDER)
10. [ ] Add unit tests

**Files to Create**:
- `agent-engine/core/cli/base.py`
- `agent-engine/core/cli/executor.py`
- `agent-engine/core/cli/providers/claude/__init__.py`
- `agent-engine/core/cli/providers/claude/executor.py`
- `agent-engine/core/cli/providers/claude/config.py`
- `agent-engine/core/cli/providers/cursor/__init__.py`
- `agent-engine/core/cli/providers/cursor/executor.py`
- `agent-engine/core/cli/providers/cursor/config.py`

### Task 4.2: Task Worker & Queue Manager
**Priority**: CRITICAL
**Duration**: 3 days
**Dependencies**: Task 4.1

#### Subtasks:
1. [ ] Create `agent-engine/core/queue_manager.py`
2. [ ] Implement Redis queue consumer
3. [ ] Add task popping logic
4. [ ] Create `agent-engine/core/worker.py`
5. [ ] Implement task execution loop
6. [ ] Add task status updates
7. [ ] Add WebSocket notifications
8. [ ] Add error handling
9. [ ] Add graceful shutdown
10. [ ] Add unit tests

**Files to Create**:
- `agent-engine/core/queue_manager.py`
- `agent-engine/core/worker.py`
- `agent-engine/core/engine.py`

### Task 4.3: Agent Definitions Migration
**Priority**: HIGH
**Duration**: 2 days
**Dependencies**: None (can run in parallel)

#### Subtasks:
1. [ ] Create `agent-engine/.claude/` directory structure
2. [ ] Copy `claude-code-agent/.claude/CLAUDE.md`
3. [ ] Copy all agent definitions:
   - [ ] brain.md
   - [ ] planning.md
   - [ ] executor.md
   - [ ] service-integrator.md
   - [ ] self-improvement.md
   - [ ] agent-creator.md
   - [ ] skill-creator.md
   - [ ] verifier.md
   - [ ] webhook-generator.md
   - [ ] github-issue-handler.md
   - [ ] github-pr-review.md
   - [ ] jira-code-plan.md
   - [ ] slack-inquiry.md
4. [ ] Copy all skills directories
5. [ ] Update agent prompts for new architecture
6. [ ] Create mcp.json configuration
7. [ ] Test agent loading

**Files to Create**:
- `agent-engine/.claude/CLAUDE.md`
- `agent-engine/.claude/agents/*.md` (13 files)
- `agent-engine/.claude/skills/*` (multiple directories)
- `agent-engine/mcp.json`

### Task 4.4: Agent Engine Docker Configuration
**Priority**: HIGH
**Duration**: 1 day
**Dependencies**: Tasks 4.1-4.3

#### Subtasks:
1. [ ] Create `agent-engine/Dockerfile`
2. [ ] Install Claude CLI
3. [ ] Install dependencies
4. [ ] Configure for scalability
5. [ ] Add environment variables
6. [ ] Create docker-compose.agent.yml
7. [ ] Test single instance
8. [ ] Test 3 replicas
9. [ ] Test MCP connections
10. [ ] Add health check

**Files to Create**:
- `agent-engine/Dockerfile`
- `agent-engine/docker-compose.agent.yml`
- `agent-engine/.env.example`

## Testing Strategy

### Unit Tests
- [ ] CLI provider interface
- [ ] Queue manager
- [ ] Task worker
- [ ] MCP server tools

### Integration Tests
- [ ] MCP server → API service communication
- [ ] Agent engine → MCP server communication
- [ ] Redis queue → Worker communication
- [ ] WebSocket notifications

### E2E Tests
- [ ] Webhook → Task → Execution flow
- [ ] Dashboard → Agent engine flow
- [ ] Multi-agent orchestration

## Deployment Checklist

### Phase 3 Deployment (MCP Servers)
- [ ] Create agent-network: `docker network create agent-network`
- [ ] Start API services: `cd api-services && docker-compose -f docker-compose.services.yml up -d`
- [ ] Build MCP servers: `cd mcp-servers && docker-compose -f docker-compose.mcp.yml build`
- [ ] Start MCP servers: `cd mcp-servers && docker-compose -f docker-compose.mcp.yml up -d`
- [ ] Verify all 4 MCP servers are running: `docker ps | grep mcp`
- [ ] Test health checks: `curl http://localhost:9001/health` (repeat for 9002, 9003, 9004)
- [ ] Test SSE connections

### Phase 4 Deployment (Agent Engine)
- [ ] Build agent engine: `cd agent-engine && docker build -t agent-engine .`
- [ ] Start single instance: `docker-compose up -d agent-engine`
- [ ] Verify MCP connections
- [ ] Test task execution
- [ ] Scale to 3 replicas: `docker-compose up -d --scale agent-engine=3`
- [ ] Verify load balancing

## Success Metrics

### Phase 3 (MCP Servers)
- [ ] All 4 MCP servers running
- [ ] All health checks passing
- [ ] SSE connections working
- [ ] API service connections working
- [ ] All tools responding correctly

### Phase 4 (Agent Engine)
- [ ] Agent engine starts successfully
- [ ] MCP connections established
- [ ] Tasks execute from Redis queue
- [ ] CLI provider switching works
- [ ] 3 replicas running and load balanced
- [ ] WebSocket notifications working

---

**Created**: 2026-01-31
**Last Updated**: 2026-01-31
**Current Phase**: Phase 3 (MCP Servers)
**Next Phase**: Phase 4 (Agent Engine)
