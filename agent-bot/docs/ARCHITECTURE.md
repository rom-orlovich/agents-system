# Complete Containerized Agent Architecture

## Overview

A fully containerized, scalable multi-agent system where **each service runs in its own Docker container** for maximum isolation, scalability, and maintainability.

---

## Container Architecture

### Total Containers: 14

1. **Agent Engine** (Scalable) - Ports 8080-8089
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

---

## System Diagram

```
External Services (GitHub, Jira, Slack, Sentry)
                      │
                      ▼
        ┌─────────────────────────┐
        │   API Gateway :8000     │
        │  ┌──────────────────┐  │
        │  │ GitHub Webhook   │  │
        │  │ Jira Webhook     │  │
        │  │ Slack Webhook    │  │
        │  │ Sentry Webhook   │  │
        │  └──────────────────┘  │
        └─────────────────────────┘
          │                    │
          ▼                    ▼
    ┌──────────┐      ┌────────────────┐
    │  Redis   │      │ Knowledge      │
    │  :6379   │      │ Graph :4000    │
    └──────────┘      └────────────────┘
          │
          ▼
┌──────────────────────────────────────┐
│    Agent Engine :8080-8089           │
│  (Scalable - Multiple Instances)     │
│  ┌────────────────────────────────┐ │
│  │ mcp.json                       │ │
│  │ - github-mcp:9001/sse          │ │
│  │ - jira-mcp:9002/sse            │ │
│  │ - slack-mcp:9003/sse           │ │
│  │ - sentry-mcp:9004/sse          │ │
│  └────────────────────────────────┘ │
└──────────────────────────────────────┘
          │ (SSE Connections)
          ▼
┌─────────────────────────────────────────────────┐
│     MCP Servers (Each in Own Container)         │
│  ┌──────────┬──────────┬──────────┬──────────┐ │
│  │ GitHub   │  Jira    │  Slack   │ Sentry   │ │
│  │  MCP     │  MCP     │  MCP     │  MCP     │ │
│  │ :9001    │ :9002    │ :9003    │ :9004    │ │
│  │(Official)│(FastMCP) │(FastMCP) │(FastMCP) │ │
│  └──────────┴──────────┴──────────┴──────────┘ │
└─────────────────────────────────────────────────┘
          │ (HTTP API Calls)
          ▼
┌─────────────────────────────────────────────────┐
│   API Services (Each in Own Container)          │
│  ┌──────────┬──────────┬──────────┬──────────┐ │
│  │ GitHub   │  Jira    │  Slack   │ Sentry   │ │
│  │  API     │  API     │  API     │  API     │ │
│  │ :3001    │ :3002    │ :3003    │ :3004    │ │
│  │ (Token)  │ (APIKey) │ (Token)  │ (DSN)    │ │
│  └──────────┴──────────┴──────────┴──────────┘ │
└─────────────────────────────────────────────────┘
          │
          ▼
External Services (GitHub, Jira, Slack, Sentry)
```

---

## Complete Project Structure

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
│   ├── dashboard/
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
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   └── server.py
│   │   ├── client/
│   │   │   ├── __init__.py
│   │   │   └── github_client.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       └── error_handler.py
│   ├── jira-api/                    # Jira API Service :3002
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   └── server.py
│   │   ├── client/
│   │   │   ├── __init__.py
│   │   │   └── jira_client.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       └── error_handler.py
│   ├── slack-api/                   # Slack API Service :3003
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   └── server.py
│   │   ├── client/
│   │   │   ├── __init__.py
│   │   │   └── slack_client.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       └── error_handler.py
│   └── sentry-api/                  # Sentry API Service :3004
│       ├── Dockerfile
│       ├── main.py
│       ├── requirements.txt
│       ├── api/
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   └── server.py
│       ├── client/
│       │   ├── __init__.py
│       │   └── sentry_client.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py
│       └── middleware/
│           ├── __init__.py
│           ├── auth.py
│           └── error_handler.py
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
│   │   │   ├── __init__.py
│   │   │   ├── handler.py
│   │   │   ├── validator.py
│   │   │   └── events.py
│   │   ├── slack/
│   │   │   ├── __init__.py
│   │   │   ├── handler.py
│   │   │   ├── validator.py
│   │   │   └── events.py
│   │   └── sentry/
│   │       ├── __init__.py
│   │       ├── handler.py
│   │       ├── validator.py
│   │       └── events.py
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
├── external-dashboard/              # External Dashboard :3001
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── static/
│   │   │   ├── css/
│   │   │   ├── js/
│   │   │   └── assets/
│   │   ├── templates/
│   │   │   ├── index.html
│   │   │   ├── agents.html
│   │   │   ├── tasks.html
│   │   │   └── monitoring.html
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

---

## Port Mapping

| Service | Port(s) | Container Name | Purpose |
|---------|---------|----------------|---------|
| Agent Engine | 8080-8089 | agent-engine-{1,2,3} | Task execution |
| GitHub MCP | 9001 | github-mcp | Official GitHub MCP server |
| Jira MCP | 9002 | jira-mcp | Custom Jira MCP server |
| Slack MCP | 9003 | slack-mcp | Custom Slack MCP server |
| Sentry MCP | 9004 | sentry-mcp | Custom Sentry MCP server |
| GitHub API | 3001 | github-api | GitHub API client |
| Jira API | 3002 | jira-api | Jira API client |
| Slack API | 3003 | slack-api | Slack API client |
| Sentry API | 3004 | sentry-api | Sentry API client |
| API Gateway | 8000 | api-gateway | Webhook reception |
| Internal Dashboard API | 5000 | internal-dashboard-api | Agent management API |
| External Dashboard | 3002 | external-dashboard | Public monitoring dashboard |
| Knowledge Graph | 4000 | knowledge-graph | Graph API |
| Redis | 6379 | redis | Task queue |
| PostgreSQL | 5432 | postgres | Database |

---

## MCP Configuration (agent-engine/mcp.json)

```json
{
  "mcpServers": {
    "github": {
      "url": "http://github-mcp:9001/sse",
      "transport": "sse",
      "note": "Official GitHub MCP (github/github-mcp-server)"
    },
    "jira": {
      "url": "http://jira-mcp:9002/sse",
      "transport": "sse",
      "note": "Custom Jira MCP (FastMCP)"
    },
    "slack": {
      "url": "http://slack-mcp:9003/sse",
      "transport": "sse",
      "note": "Custom Slack MCP (FastMCP)"
    },
    "sentry": {
      "url": "http://sentry-mcp:9004/sse",
      "transport": "sse",
      "note": "Custom Sentry MCP (FastMCP)"
    }
  }
}
```

---

## Docker Compose Files

### Main docker-compose.yml

```yaml
version: '3.8'

services:
  # Infrastructure
  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    networks:
      - agent-network
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=agents_system
      - POSTGRES_USER=agent
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    networks:
      - agent-network
    restart: unless-stopped

  # API Gateway
  api-gateway:
    build: ./api-gateway
    container_name: api-gateway
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - KNOWLEDGE_GRAPH_URL=http://knowledge-graph:4000
      - GITHUB_API_URL=http://github-api:3001
      - JIRA_API_URL=http://jira-api:3002
      - SLACK_API_URL=http://slack-api:3003
      - SENTRY_API_URL=http://sentry-api:3004
    depends_on:
      - redis
    networks:
      - agent-network
    restart: unless-stopped

  # Knowledge Graph
  knowledge-graph:
    build: ./knowledge-graph
    container_name: knowledge-graph
    ports:
      - "4000:4000"
    networks:
      - agent-network
    restart: unless-stopped

  # Internal Dashboard API
  internal-dashboard-api:
    build: ./internal-dashboard-api
    container_name: internal-dashboard-api
    ports:
      - "5000:5000"
    environment:
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgres
      - AGENT_ENGINE_URL=http://agent-engine:8080
    depends_on:
      - redis
      - postgres
    networks:
      - agent-network
    restart: unless-stopped

  # External Dashboard
  external-dashboard:
    build: ./external-dashboard
    container_name: external-dashboard
    ports:
      - "3002:3002"
    environment:
      - INTERNAL_API_URL=http://internal-dashboard-api:5000
    depends_on:
      - internal-dashboard-api
    networks:
      - agent-network
    restart: unless-stopped

  # Agent Engine (Scalable)
  agent-engine:
    build: ./agent-engine
    ports:
      - "8080-8089:8080"
    environment:
      - CLI_PROVIDER=claude-code-cli
      - REDIS_HOST=redis
      - KNOWLEDGE_GRAPH_URL=http://knowledge-graph:4000
    depends_on:
      - redis
    networks:
      - agent-network
    restart: unless-stopped
    deploy:
      replicas: 3

networks:
  agent-network:
    driver: bridge
```

### mcp-servers/docker-compose.mcp.yml

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

networks:
  agent-network:
    external: true
```

### api-services/docker-compose.services.yml

```yaml
version: '3.8'

services:
  github-api:
    build: ./github-api
    container_name: github-api
    ports:
      - "3001:3001"
    environment:
      - PORT=3001
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    networks:
      - agent-network
    restart: unless-stopped

  jira-api:
    build: ./jira-api
    container_name: jira-api
    ports:
      - "3002:3002"
    environment:
      - PORT=3002
      - JIRA_API_KEY=${JIRA_API_KEY}
      - JIRA_URL=${JIRA_URL}
      - JIRA_EMAIL=${JIRA_EMAIL}
    networks:
      - agent-network
    restart: unless-stopped

  slack-api:
    build: ./slack-api
    container_name: slack-api
    ports:
      - "3003:3003"
    environment:
      - PORT=3003
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
    networks:
      - agent-network
    restart: unless-stopped

  sentry-api:
    build: ./sentry-api
    container_name: sentry-api
    ports:
      - "3004:3004"
    environment:
      - PORT=3004
      - SENTRY_DSN=${SENTRY_DSN}
    networks:
      - agent-network
    restart: unless-stopped

networks:
  agent-network:
    external: true
```

---

## Deployment

### 1. Create Network
```bash
docker network create agent-network
```

### 2. Start Infrastructure
```bash
docker-compose up -d redis postgres
```

### 3. Start API Services
```bash
cd api-services
docker-compose -f docker-compose.services.yml up -d
cd ..
```

### 4. Start MCP Servers
```bash
cd mcp-servers
docker-compose -f docker-compose.mcp.yml up -d
cd ..
```

### 5. Start Remaining Services
```bash
docker-compose up -d api-gateway knowledge-graph internal-dashboard-api external-dashboard
```

### 6. Start Agent Engine (3 replicas)
```bash
docker-compose up -d --scale agent-engine=3 agent-engine
```

### Scale Agent Engine
```bash
docker-compose up -d --scale agent-engine=5
```

### View All Containers
```bash
docker ps
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f agent-engine

# MCP servers
cd mcp-servers && docker-compose -f docker-compose.mcp.yml logs -f github-mcp

# API services
cd api-services && docker-compose -f docker-compose.services.yml logs -f github-api
```

---

## Key Benefits

### 1. **Maximum Isolation**
- Each service in own container
- Failure in one doesn't affect others
- Easy to debug and monitor

### 2. **Independent Scaling**
- Scale agent-engine horizontally (1-N)
- Scale each MCP server independently
- Scale each API service independently

### 3. **Security**
- API keys only in API service containers
- No keys in MCP servers
- No keys in webhooks
- Centralized key management per service

### 4. **Maintainability**
- Update one service without affecting others
- Clear boundaries and responsibilities
- Easy to add new services

### 5. **Flexibility**
- Use official GitHub MCP
- Custom MCP servers for other services
- Easy to switch CLI providers
- Easy to add new services

---

## CLI Provider Architecture

The Agent Engine supports multiple CLI providers through a modular, plugin-based architecture. Each provider is isolated in its own folder with a standardized interface.

### Provider Structure

```
core/cli/
├── executor.py                      # Main executor (provider-agnostic)
├── base.py                          # Base provider interface
└── providers/
    ├── claude/                      # Claude Code CLI provider
    │   ├── __init__.py
    │   ├── executor.py              # Claude-specific implementation
    │   └── config.py                # Claude configuration
    └── cursor/                      # Cursor CLI provider
        ├── __init__.py
        ├── executor.py              # Cursor-specific implementation
        └── config.py                # Cursor configuration
```

### Base Provider Interface (base.py)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseCLIProvider(ABC):
    """Base interface for all CLI providers"""
    
    @abstractmethod
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task using the CLI provider"""
        pass
    
    @abstractmethod
    def supports_mcp(self) -> bool:
        """Check if provider supports MCP"""
        pass
    
    @abstractmethod
    def get_config_path(self) -> str:
        """Get configuration directory path"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the CLI provider"""
        pass
```

### Main Executor (executor.py)

```python
import os
from typing import Dict, Any
from .providers.claude.executor import ClaudeExecutor
from .providers.cursor.executor import CursorExecutor

class CLIExecutor:
    """Main CLI executor that delegates to specific providers"""
    
    def __init__(self):
        self.provider_name = os.getenv('CLI_PROVIDER', 'claude-code-cli')
        self.provider = self._load_provider()
    
    def _load_provider(self):
        """Load the appropriate CLI provider"""
        if self.provider_name == 'claude-code-cli':
            return ClaudeExecutor()
        elif self.provider_name == 'cursor-cli':
            return CursorExecutor()
        else:
            raise ValueError(f"Unknown CLI provider: {self.provider_name}")
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task using the configured provider"""
        return self.provider.execute_task(task)
```

### Claude Provider (providers/claude/executor.py)

```python
from ..base import BaseCLIProvider
from typing import Dict, Any

class ClaudeExecutor(BaseCLIProvider):
    """Claude Code CLI provider implementation"""
    
    def __init__(self):
        self.command = "claude"
        self.config_path = ".claude/"
    
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task using Claude Code CLI"""
        # Implementation for Claude CLI execution
        pass
    
    def supports_mcp(self) -> bool:
        return True
    
    def get_config_path(self) -> str:
        return self.config_path
    
    def initialize(self) -> bool:
        """Initialize Claude CLI"""
        # Run: claude init
        pass
```

### Cursor Provider (providers/cursor/executor.py)

```python
from ..base import BaseCLIProvider
from typing import Dict, Any

class CursorExecutor(BaseCLIProvider):
    """Cursor CLI provider implementation"""
    
    def __init__(self):
        self.command = "cursor"
        self.config_path = ".cursor/"
    
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task using Cursor CLI"""
        # Implementation for Cursor CLI execution
        pass
    
    def supports_mcp(self) -> bool:
        return True
    
    def get_config_path(self) -> str:
        return self.config_path
    
    def initialize(self) -> bool:
        """Initialize Cursor CLI"""
        # Run: cursor init
        pass
```

### Provider Configuration

**Claude Provider (providers/claude/config.py)**
```python
CLAUDE_CONFIG = {
    "command": "claude",
    "supports_mcp": True,
    "supports_git": True,
    "config_path": ".claude/",
    "init_command": "claude init",
    "mcp_config_file": "mcp.json"
}
```

**Cursor Provider (providers/cursor/config.py)**
```python
CURSOR_CONFIG = {
    "command": "cursor",
    "supports_mcp": True,
    "supports_git": True,
    "config_path": ".cursor/",
    "init_command": "cursor init",
    "mcp_config_file": "mcp.json"
}
```

### Environment Configuration

```bash
# Set CLI provider (default: claude-code-cli)
CLI_PROVIDER=claude-code-cli  # or cursor-cli

# Provider-specific settings
CLAUDE_API_KEY=${CLAUDE_API_KEY}
CURSOR_API_KEY=${CURSOR_API_KEY}
```

### Usage in Worker

```python
from core.cli.executor import CLIExecutor

class TaskWorker:
    def __init__(self):
        self.cli_executor = CLIExecutor()  # Auto-loads from CLI_PROVIDER env
    
    def process_task(self, task):
        result = self.cli_executor.execute(task)
        return result
```

### Adding New Providers

To add a new CLI provider:

1. Create provider folder: `core/cli/providers/new-provider/`
2. Implement `executor.py` extending `BaseCLIProvider`
3. Add `config.py` with provider configuration
4. Update main `executor.py` to load new provider
5. Set `CLI_PROVIDER=new-provider` in environment

---

## Summary

**Total Containers**: 14 separate Docker containers  
**Scalable**: Agent Engine (1-N instances)  
**MCP Servers**: 4 separate containers (GitHub official, Jira/Slack/Sentry custom)  
**API Services**: 4 separate containers (one per external service)  
**Dashboards**: 2 separate containers (Internal API + External Dashboard)  
**CLI Providers**: Modular architecture supporting Claude Code CLI and Cursor CLI  
**Architecture**: Fully containerized, microservices-based  
**Communication**: HTTP/SSE between containers  
**Security**: API keys isolated in API service containers, no rate limiting  
**Deployment**: Docker Compose orchestration  
