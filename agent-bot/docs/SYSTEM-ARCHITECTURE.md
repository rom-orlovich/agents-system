# Agent Bot System Architecture

A comprehensive guide to the full system architecture, explaining each component and how they work together.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Service Components](#service-components)
4. [Data Flows](#data-flows)
5. [OAuth & Authentication](#oauth--authentication)
6. [Knowledge System (Optional)](#knowledge-system-optional)
7. [Independence & Modularity](#independence--modularity)
8. [Configuration](#configuration)

---

## System Overview

Agent Bot is a microservices-based AI agent system that:

- **Receives webhooks** from GitHub, Jira, Slack, and Sentry
- **Executes AI tasks** using Claude or Cursor CLI
- **Indexes knowledge** from code repositories and documentation
- **Responds autonomously** to the originating service

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SERVICES                               │
│     GitHub    │    Jira    │   Confluence   │    Slack    │    Sentry       │
└───────┬───────────┬────────────────┬────────────┬─────────────┬─────────────┘
        │           │                │            │             │
        │     OAuth Tokens           │     Webhooks             │
        ▼           ▼                ▼            ▼             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENT-BOT SYSTEM                                │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        PRESENTATION LAYER                              │ │
│  │   External Dashboard (React)  ◄──►  Dashboard API (FastAPI)           │ │
│  │        Port: 3005                       Port: 5000                     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        CORE SERVICES LAYER                             │ │
│  │                                                                        │ │
│  │   Agent Engine     OAuth Service     Webhook Server     Task Logger    │ │
│  │    Port: 8080       Port: 8010        Port: 8000        Port: 8090    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    KNOWLEDGE LAYER (OPTIONAL)                          │ │
│  │                                                                        │ │
│  │   LlamaIndex      GKG Service      Indexer Worker       MCP Servers   │ │
│  │   Port: 8100       Port: 8003       Port: 8004        Ports: 9001-9005│ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          DATA LAYER                                    │ │
│  │                                                                        │ │
│  │       PostgreSQL           Redis              ChromaDB                 │ │
│  │       Port: 5432         Port: 6379          Port: 8000               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Layers

### Layer 1: Presentation Layer

**Purpose**: User interface and API for system management

| Component | Port | Description |
|-----------|------|-------------|
| **External Dashboard** | 3005 | React UI for monitoring and configuration |
| **Dashboard API** | 5000 | FastAPI backend for dashboard |

**Features**:
- Real-time task monitoring via WebSocket
- Data source configuration
- OAuth integration management
- Analytics and metrics

---

### Layer 2: Core Services Layer

**Purpose**: Main business logic and external service integration

| Component | Port | Description |
|-----------|------|-------------|
| **Agent Engine** | 8080 | Executes AI tasks using Claude/Cursor CLI |
| **OAuth Service** | 8010 | Manages OAuth tokens for GitHub, Jira, Slack |
| **Webhook Server** | 8000 | Receives webhooks from external services |
| **Task Logger** | 8090 | Logs task output and status |

**Key Feature**: These services work **independently** of the knowledge layer.

---

### Layer 3: Knowledge Layer (Optional)

**Purpose**: Semantic search and code analysis for enhanced AI context

| Component | Port | Description |
|-----------|------|-------------|
| **LlamaIndex Service** | 8100 | Vector search over indexed content |
| **GKG Service** | 8003 | Code relationship graph analysis |
| **Indexer Worker** | 8004 | Indexes data from GitHub, Jira, Confluence |
| **ChromaDB** | 8000 | Vector database for embeddings |
| **MCP Servers** | 9001-9005 | Tool interfaces for AI agents |

**Key Feature**: This entire layer can be **enabled or disabled** without affecting core functionality.

---

### Layer 4: Data Layer

**Purpose**: Persistent storage

| Component | Port | Description |
|-----------|------|-------------|
| **PostgreSQL** | 5432 | Relational data (users, sources, jobs, tokens) |
| **Redis** | 6379 | Task queues, caching, pub/sub |
| **ChromaDB** | 8000 | Vector embeddings for semantic search |

---

## Service Components

### 1. Agent Engine

**Purpose**: Executes AI agent tasks using CLI providers

**Location**: `agent-engine/`

```
agent-engine/
├── main.py              # FastAPI app, task worker
├── config/settings.py   # Configuration
├── cli/                 # CLI provider implementations
│   ├── providers/
│   │   ├── claude.py    # Claude CLI wrapper
│   │   └── cursor.py    # Cursor CLI wrapper
│   └── factory.py       # CLI factory
└── services/
    └── knowledge.py     # Knowledge service client (optional)
```

**API Endpoints**:
```
POST /tasks              → Create new task
GET  /tasks/{id}         → Get task status
GET  /health             → Health check
GET  /health/detailed    → Detailed component status
POST /knowledge/toggle   → Enable/disable knowledge services
```

**Key Features**:
- Supports Claude and Cursor CLI providers
- Graceful degradation without knowledge services
- Horizontal scaling via Redis queue

---

### 2. OAuth Service

**Purpose**: Manages OAuth tokens for external service authentication

**Location**: `oauth-service/`

```
oauth-service/
├── main.py
├── api/routes.py        # OAuth endpoints
├── providers/           # OAuth provider implementations
│   ├── github.py        # GitHub App OAuth
│   ├── jira.py          # Jira/Atlassian OAuth (PKCE)
│   └── slack.py         # Slack OAuth
└── services/
    ├── token_service.py       # Token retrieval & refresh
    └── installation_service.py # Installation management
```

**API Endpoints**:
```
GET  /oauth/install/{platform}        → Start OAuth flow
GET  /oauth/callback/{platform}       → OAuth callback
GET  /oauth/installations             → List installations
GET  /oauth/token/{platform}          → Get valid token
DELETE /oauth/installations/{id}      → Revoke installation
```

**Supported Platforms**:
| Platform | OAuth Type | Token Refresh |
|----------|------------|---------------|
| GitHub | App Installation | Auto (1h expiry) |
| Jira | PKCE OAuth 2.0 | Yes (refresh token) |
| Slack | OAuth 2.0 | No |

---

### 3. Dashboard API

**Purpose**: Backend API for the dashboard UI

**Location**: `dashboard-api/`

```
dashboard-api/
├── main.py
└── api/
    ├── sources.py       # Data source CRUD + OAuth validation
    ├── oauth_status.py  # OAuth connection status
    ├── analytics.py     # Task analytics
    ├── conversations.py # Chat history
    └── websocket.py     # Real-time updates
```

**Key Features**:
- Validates OAuth connection before enabling data sources
- Real-time task status via WebSocket
- Analytics aggregation

---

### 4. LlamaIndex Service

**Purpose**: Semantic search over indexed content

**Location**: `llamaindex-service/`

```
llamaindex-service/
├── main.py
├── core/
│   ├── interfaces.py    # Protocol definitions
│   ├── query_engine.py  # Search implementation
│   └── models.py        # Data models
├── adapters/
│   └── chromadb_adapter.py  # Vector store adapter
└── factory.py           # Dependency injection
```

**API Endpoints**:
```
POST /query              → Semantic search
POST /index              → Index documents
GET  /collections        → List collections
GET  /health             → Health check
```

**Collections**:
- `code_{org_id}` - Code chunks
- `jira_{org_id}` - Jira issues
- `confluence_{org_id}` - Documentation

---

### 5. GKG Service (GitLab Knowledge Graph)

**Purpose**: Code relationship analysis

**Location**: `gkg-service/`

```
gkg-service/
├── main.py
├── core/
│   ├── interfaces.py      # Protocol definitions
│   ├── graph_analyzer.py  # Analysis implementation
│   └── models.py          # Data models
└── adapters/
    └── gkg_binary_adapter.py  # GKG binary wrapper
```

**API Endpoints**:
```
POST /graph/analyze      → Analyze repository
POST /graph/related      → Find related entities
GET  /graph/entities     → List entities
GET  /health             → Health check
```

**Relationships Tracked**:
- Function calls
- Class inheritance
- Module imports
- File dependencies

---

### 6. Indexer Worker

**Purpose**: Indexes data from external sources

**Location**: `indexer-worker/`

```
indexer-worker/
├── main.py
├── core/
│   ├── interfaces.py     # Protocol definitions
│   ├── orchestrator.py   # Job orchestration
│   └── models.py         # Data models
├── indexers/
│   ├── github_indexer.py     # GitHub repository indexer
│   ├── jira_indexer.py       # Jira issue indexer
│   └── confluence_indexer.py # Confluence page indexer
└── services/
    └── token_client.py   # OAuth token retrieval
```

**Process**:
1. Get job from Redis queue `indexer:jobs`
2. Fetch OAuth token from OAuth Service
3. Pull data from external API
4. Generate embeddings
5. Store in ChromaDB (vectors) and GKG (relationships)
6. Update job status in PostgreSQL

---

## Data Flows

### Flow 1: Task Execution (Core Only)

```
User/Webhook → Webhook Server → Redis Queue → Agent Engine → Claude CLI → Result
                                    │                            │
                                    └── PostgreSQL ◄─────────────┘
```

### Flow 2: Task Execution with Knowledge

```
User/Webhook → Webhook Server → Redis Queue → Agent Engine
                                                   │
                                    ┌──────────────┼──────────────┐
                                    ▼              ▼              ▼
                              LlamaIndex       GKG Service    Claude CLI
                                    │              │              │
                                    └──────────────┼──────────────┘
                                                   ▼
                                                Result
```

### Flow 3: Data Source Indexing

```
UI → Dashboard API → Validate OAuth → Create Source
                           │
                           ▼
                     PostgreSQL
                           │
                           ▼
                  Redis Queue (indexer:jobs)
                           │
                           ▼
                    Indexer Worker
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
      OAuth Service    GitHub API    ChromaDB
      (get token)      (fetch data)  (store vectors)
```

### Flow 4: OAuth Token Usage

```
Service needs token → Token Client → OAuth Service → PostgreSQL
                                           │
                                           ▼
                                    Check expiration
                                           │
                            ┌──────────────┼──────────────┐
                            ▼                             ▼
                      Token valid                   Token expired
                            │                             │
                            │                     Refresh from provider
                            │                             │
                            └──────────────┬──────────────┘
                                           ▼
                                     Return token
```

---

## OAuth & Authentication

### How OAuth Works in Agent Bot

1. **User connects service** via Integrations page
2. **OAuth flow** redirects to provider (GitHub, Jira, etc.)
3. **User authorizes** the application
4. **Token stored** in PostgreSQL (encrypted)
5. **Services request tokens** via OAuth Service API
6. **Auto-refresh** happens transparently

### Token Access Pattern

```python
# In any service that needs external API access
token = await token_client.get_token(platform="github", org_id="org-123")

# Use token
response = await httpx.get(
    "https://api.github.com/repos/...",
    headers={"Authorization": f"token {token}"}
)
```

### OAuth Integration with Data Sources

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Data Source    │────►│  Dashboard API  │────►│  OAuth Service  │
│  (UI or API)    │     │  (validates)    │     │  (checks token) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌───────────────────────────────┘
                        ▼
              Token exists and valid?
                        │
         ┌──────────────┼──────────────┐
         ▼                             ▼
    Yes: Allow                    No: Reject
    enable source              "Connect OAuth first"
```

---

## Knowledge System (Optional)

### What It Does

The knowledge system provides:
1. **Semantic search** - Find relevant code/docs by meaning
2. **Code relationships** - Understand function calls, imports
3. **Context for AI** - Better responses with more context

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE SYSTEM                             │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   GitHub    │  │    Jira     │  │ Confluence  │  Sources     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          ▼                                       │
│                  ┌───────────────┐                               │
│                  │Indexer Worker │  Fetches & processes          │
│                  └───────┬───────┘                               │
│                          │                                       │
│         ┌────────────────┼────────────────┐                      │
│         ▼                ▼                ▼                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  ChromaDB   │  │LlamaIndex   │  │GKG Service  │              │
│  │  (vectors)  │  │  (search)   │  │  (graph)    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                          │                                       │
│                          ▼                                       │
│                  ┌───────────────┐                               │
│                  │ Agent Engine  │  Uses context                 │
│                  └───────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### Enabling/Disabling

**Via Environment Variable**:
```bash
KNOWLEDGE_SERVICES_ENABLED=true   # Enable
KNOWLEDGE_SERVICES_ENABLED=false  # Disable (default)
```

**Via Docker Compose Profile**:
```bash
docker-compose up                         # Core only
docker-compose --profile knowledge up     # Core + Knowledge
```

**Via API** (runtime):
```bash
curl -X POST "http://localhost:8080/knowledge/toggle?enabled=true"
```

---

## Independence & Modularity

### Design Principles

1. **Services are independent** - Each service has its own responsibility
2. **Protocols over implementations** - Use interfaces for dependency injection
3. **Graceful degradation** - System works even if optional services are down
4. **Feature flags** - Enable/disable features without code changes

### What Works Without What

| If This Is Down... | These Still Work |
|--------------------|------------------|
| Knowledge Services | Agent Engine, OAuth, Dashboard |
| LlamaIndex | GKG Service, Indexer (partial) |
| GKG Service | LlamaIndex, Indexer (partial) |
| OAuth Service | Agent Engine (with static tokens) |
| ChromaDB | Agent Engine, OAuth, Dashboard |

### Service Dependencies

```
Required for ALL:
└── PostgreSQL, Redis

Required for Core:
└── Agent Engine
    └── Redis (task queue)

Required for Knowledge:
└── Indexer Worker
    ├── OAuth Service (tokens)
    ├── ChromaDB (storage)
    └── External APIs (GitHub, Jira)

└── LlamaIndex Service
    └── ChromaDB (vectors)

└── GKG Service
    └── None (standalone)
```

---

## Configuration

### Essential Environment Variables

```bash
# Database
POSTGRES_URL=postgresql://agent:agent@postgres:5432/agent_system
REDIS_URL=redis://redis:6379/0

# CLI Provider
CLI_PROVIDER=claude                    # or "cursor"
ANTHROPIC_API_KEY=sk-ant-xxx          # For Claude

# Knowledge Services (optional)
KNOWLEDGE_SERVICES_ENABLED=false       # Enable knowledge layer
LLAMAINDEX_URL=http://llamaindex-service:8100
KNOWLEDGE_GRAPH_URL=http://gkg-service:8003

# OAuth Service
OAUTH_SERVICE_URL=http://oauth-service:8010

# Indexer Worker
USE_OAUTH=true                         # Use OAuth for API access
CHROMADB_URL=http://chromadb:8000
```

### Service-Specific Configuration

See each service's README.md for detailed configuration:
- [agent-engine/README.md](../agent-engine/README.md)
- [oauth-service/README.md](../oauth-service/README.md)
- [llamaindex-service/README.md](../llamaindex-service/README.md)
- [gkg-service/README.md](../gkg-service/README.md)
- [indexer-worker/README.md](../indexer-worker/README.md)

---

## Quick Reference

### Ports

| Port | Service |
|------|---------|
| 3005 | External Dashboard |
| 5000 | Dashboard API |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 8000 | Webhook Server / ChromaDB |
| 8003 | GKG Service |
| 8004 | Indexer Worker |
| 8010 | OAuth Service |
| 8080 | Agent Engine |
| 8090 | Task Logger |
| 8100 | LlamaIndex Service |
| 9001-9005 | MCP Servers |

### Health Checks

```bash
# Core Services
curl http://localhost:8080/health          # Agent Engine
curl http://localhost:5000/health          # Dashboard API
curl http://localhost:8010/health          # OAuth Service

# Knowledge Services
curl http://localhost:8100/health          # LlamaIndex
curl http://localhost:8003/health          # GKG Service
curl http://localhost:8004/health          # Indexer Worker
```

### Starting the System

```bash
# Core only (no knowledge)
docker-compose up

# With knowledge layer
docker-compose --profile knowledge up

# Scale agent workers
docker-compose up -d --scale agent-engine=3
```
