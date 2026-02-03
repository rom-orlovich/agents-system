# Knowledge System Integration Architecture

> **Enterprise Knowledge Graph & RAG System for Agent Bot**
>
> Integration of ChromaDB, LlamaIndex, and GitLab Knowledge Graph (GKG) with a two-tier architecture: basic knowledge tools in the core system, advanced features as optional services.

---

## Quick Start

### Basic Knowledge Tools (Core System)

ChromaDB and basic knowledge tools are included in the main docker-compose:

```bash
cd agent-bot
make up                  # Starts all core services including ChromaDB
```

Basic tools available via `knowledge-graph-mcp`:
- `knowledge_store` - Store documents in ChromaDB
- `knowledge_query` - Semantic search
- `knowledge_collections` - Manage collections
- `knowledge_update` / `knowledge_delete` - CRUD operations

### Advanced Knowledge Services (Optional)

For enterprise features (hybrid RAG, code graph, background indexing):

```bash
make knowledge-up        # Start LlamaIndex, GKG, Indexer
make up-full             # Start everything including advanced features
```

Advanced tools available:
- **LlamaIndex MCP** (:9006) - Hybrid search, code search, Jira/Confluence search
- **GKG MCP** (:9007) - Dependency analysis, call graphs, class hierarchies

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Service Specifications](#service-specifications)
4. [Data Sources Configuration](#data-sources-configuration)
5. [Database Schema Extensions](#database-schema-extensions)
6. [MCP Server Implementations](#mcp-server-implementations)
7. [Dashboard UI Extensions](#dashboard-ui-extensions)
8. [Indexing Pipeline](#indexing-pipeline)
9. [Query Flow Architecture](#query-flow-architecture)
10. [Docker Services Configuration](#docker-services-configuration)
11. [Implementation Plan](#implementation-plan)
12. [Security Considerations](#security-considerations)

---

## Executive Summary

This document describes the **two-tier knowledge system** integrated into Agent Bot:

### Tier 1: Core Knowledge (Always Available)

| System | Purpose | Port | Status |
|--------|---------|------|--------|
| **ChromaDB** | Vector embeddings for semantic search | 8001 | Core |
| **Knowledge Graph MCP** | Basic knowledge tools (store, query, CRUD) | 9005 | Core |

### Tier 2: Advanced Knowledge (Optional Profile)

| System | Purpose | Port | Status |
|--------|---------|------|--------|
| **LlamaIndex Service** | Hybrid RAG orchestration (vectors + graphs) | 8002 | Optional |
| **LlamaIndex MCP** | Advanced search tools | 9006 | Optional |
| **GKG Service** | GitLab Knowledge Graph (code relationships) | 8003 | Optional |
| **GKG MCP** | Code graph query tools | 9007 | Optional |
| **Indexer Worker** | Background indexing (GitHub, Jira, Confluence) | 8004 | Optional |

**Key Design Principles:**

1. **Two-Tier Architecture** - Basic features in core, advanced features via Docker profile
2. **Configurable Data Sources** - UI-driven selection of repos, Jira projects, Confluence spaces
3. **Organization-Agnostic** - Multi-tenant support with `org_id` partitioning
4. **Modular MCP Integration** - Each service exposes tools via MCP protocol
5. **No External Orchestration** - No n8n; Redis pub/sub for event-driven indexing
6. **Profile-Based Deployment** - Use `--profile knowledge` for advanced features

---

## Architecture Overview

### Updated System Topology (21 Microservices)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT BOT SYSTEM                                  │
│                      (18 + 3 Knowledge Services)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ENTRY LAYER                        EXECUTION LAYER                         │
│  ├─ API Gateway :8000               ├─ CLI Agent Engine :8080-8089          │
│  ├─ OAuth Service :8010             │   (Claude CLI + Knowledge Skills)     │
│  └─ External Dashboard :3005        └─ Task Logger :8090                    │
│                                                                             │
│  DATA LAYER                         MCP LAYER                               │
│  ├─ GitHub API :3001                ├─ GitHub MCP :9001                     │
│  ├─ Jira API :3002                  ├─ Jira MCP :9002                       │
│  ├─ Slack API :3003                 ├─ Slack MCP :9003                      │
│  ├─ Sentry API :3004                ├─ Sentry MCP :9004                     │
│  └─ Confluence API :3006 [NEW]      ├─ Knowledge Graph MCP :9005            │
│                                     ├─ LlamaIndex MCP :9006 [NEW]           │
│                                     └─ GKG MCP :9007 [NEW]                  │
│                                                                             │
│  KNOWLEDGE LAYER [NEW]              PERSISTENCE                             │
│  ├─ ChromaDB :8001                  ├─ PostgreSQL :5432                     │
│  ├─ LlamaIndex Service :8002        │   └─ data_sources table [NEW]         │
│  └─ GKG Service :8003               ├─ Redis :6379                          │
│                                     │   └─ index:* channels [NEW]           │
│  ANALYTICS                          └─ Shared Volume: /data/repos           │
│  ├─ Dashboard API :5000                                                     │
│  └─ Indexer Worker :8004 [NEW]                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          DATA FLOW ARCHITECTURE                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. SOURCE CONFIGURATION (UI → Database)                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐              │
│  │  Dashboard  │───▶│ Dashboard   │───▶│ PostgreSQL          │              │
│  │  UI :3005   │    │ API :5000   │    │ data_sources table  │              │
│  └─────────────┘    └─────────────┘    └─────────────────────┘              │
│                                                                              │
│  2. INDEXING TRIGGER (Config → Indexer → Knowledge Services)                 │
│  ┌─────────────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │ Dashboard API       │───▶│ Redis       │───▶│ Indexer Worker :8004    │  │
│  │ POST /sources/sync  │    │ index:org   │    │ ├─ Clone filtered repos │  │
│  └─────────────────────┘    └─────────────┘    │ ├─ Fetch Jira tickets   │  │
│                                                │ ├─ Fetch Confluence     │  │
│                                                │ └─ Trigger indexing     │  │
│                                                └───────────┬─────────────┘  │
│                                                            │                │
│                              ┌─────────────────────────────┼────────────┐   │
│                              ▼                             ▼            ▼   │
│                     ┌─────────────┐           ┌─────────────┐  ┌─────────┐  │
│                     │ ChromaDB    │           │ LlamaIndex  │  │ GKG     │  │
│                     │ (vectors)   │           │ (hybrid)    │  │ (graph) │  │
│                     └─────────────┘           └─────────────┘  └─────────┘  │
│                                                                              │
│  3. QUERY FLOW (Agent → MCP → Knowledge Services)                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │ Agent       │───▶│ LlamaIndex  │───▶│ Hybrid Query Engine             │  │
│  │ Engine      │    │ MCP :9006   │    │ ├─ Vector search (ChromaDB)     │  │
│  │ (Claude)    │    │             │    │ ├─ Graph traversal (GKG)        │  │
│  └─────────────┘    └─────────────┘    │ └─ Reranking & fusion           │  │
│                                        └─────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Service Specifications

### 1. ChromaDB Service

**Purpose:** Persistent vector database for semantic embeddings of code, documentation, and tickets.

| Property | Value |
|----------|-------|
| Port | 8001 |
| Image | `chromadb/chroma:latest` |
| Storage | `/data/chromadb` (persistent volume) |
| Collections | `code`, `jira_tickets`, `confluence_docs`, `github_issues` |

**Collections Schema:**

```python
# Collection: code
{
    "id": "repo:file:hash",
    "embedding": [float...],  # 1536 dimensions (OpenAI) or 384 (sentence-transformers)
    "metadata": {
        "org_id": "acme",
        "repo": "backend-api",
        "file_path": "src/auth/handler.py",
        "language": "python",
        "chunk_type": "function",  # function, class, module, docstring
        "name": "authenticate_user",
        "line_start": 45,
        "line_end": 78,
        "indexed_at": "2024-01-15T10:30:00Z"
    },
    "document": "def authenticate_user(token: str) -> User:..."
}

# Collection: jira_tickets
{
    "id": "PROJ-123",
    "embedding": [float...],
    "metadata": {
        "org_id": "acme",
        "project": "PROJ",
        "issue_type": "Bug",
        "status": "Open",
        "priority": "High",
        "labels": ["backend", "auth"],
        "created": "2024-01-10T08:00:00Z"
    },
    "document": "Title: Login fails with OAuth tokens\n\nDescription: When users..."
}

# Collection: confluence_docs
{
    "id": "space:page:version",
    "embedding": [float...],
    "metadata": {
        "org_id": "acme",
        "space": "ENG",
        "page_title": "Authentication Architecture",
        "parent_page": "Backend Documentation",
        "labels": ["architecture", "auth"],
        "last_modified": "2024-01-12T14:00:00Z"
    },
    "document": "## Authentication Flow\n\nThe system uses OAuth 2.0..."
}
```

---

### 2. LlamaIndex Service

**Purpose:** Hybrid RAG orchestration combining vector search (ChromaDB) with graph traversal (GKG).

| Property | Value |
|----------|-------|
| Port | 8002 (HTTP API), 9006 (MCP SSE) |
| Image | Custom `llamaindex-service:latest` |
| Dependencies | ChromaDB :8001, GKG :8003 |

**Capabilities:**

1. **Hybrid Query Engine** - Combines vector similarity with graph relationships
2. **Query Routing** - Routes queries to appropriate index (code, docs, tickets)
3. **Context Assembly** - Builds rich context from multiple sources
4. **Reranking** - Cross-encoder reranking for relevance
5. **Caching** - Redis-backed query cache

**API Endpoints:**

```
POST /query                 # Hybrid query across all sources
POST /query/code            # Code-specific queries
POST /query/docs            # Documentation queries
POST /query/tickets         # Jira ticket queries
GET  /health                # Health check
POST /index/trigger         # Trigger reindexing
GET  /collections           # List available collections
```

---

### 3. GitLab Knowledge Graph (GKG) Service

**Purpose:** Code entity graph for understanding relationships, dependencies, and call hierarchies.

| Property | Value |
|----------|-------|
| Port | 8003 (HTTP API), 9007 (MCP SSE) |
| Image | Custom `gkg-service:latest` |
| Binary | GitLab `gkg` CLI (Rust) |
| Storage | `/data/gkg` (graph database) |

**Graph Entities:**

```
Nodes:
├─ Repository      (name, org, language)
├─ File            (path, language, size)
├─ Module          (name, file, exports)
├─ Class           (name, file, methods)
├─ Function        (name, file, signature)
├─ Variable        (name, scope, type)
└─ Import          (source, target)

Edges:
├─ CONTAINS        (Repository → File, File → Class, etc.)
├─ IMPORTS         (File → Module)
├─ EXTENDS         (Class → Class)
├─ IMPLEMENTS      (Class → Interface)
├─ CALLS           (Function → Function)
├─ REFERENCES      (Function → Variable)
└─ DEPENDS_ON      (Module → Module)
```

**Query Capabilities:**

```
# Find all callers of a function
gkg query "MATCH (f:Function)-[:CALLS]->(target:Function {name: 'authenticate'}) RETURN f"

# Find dependency chain
gkg query "MATCH path = (a:Module)-[:DEPENDS_ON*1..5]->(b:Module {name: 'auth'}) RETURN path"

# Find unused exports
gkg query "MATCH (e:Export) WHERE NOT ()-[:IMPORTS]->(e) RETURN e"
```

---

### 4. Indexer Worker Service

**Purpose:** Background worker that handles indexing jobs triggered by UI configuration changes.

| Property | Value |
|----------|-------|
| Port | 8004 |
| Image | Custom `indexer-worker:latest` |
| Queue | Redis `index:jobs` |

**Responsibilities:**

1. **Repository Cloning** - Clone/pull filtered repositories
2. **Code Chunking** - Split code into semantic chunks
3. **Embedding Generation** - Generate embeddings via API or local model
4. **ChromaDB Indexing** - Store vectors in appropriate collections
5. **GKG Indexing** - Run `gkg index` on cloned repos
6. **Jira Fetching** - Fetch tickets matching JQL filters
7. **Confluence Fetching** - Fetch pages from configured spaces
8. **Progress Reporting** - Publish progress to Redis pub/sub

---

### 5. Confluence API Service

**Purpose:** Credential-isolated Confluence REST API client.

| Property | Value |
|----------|-------|
| Port | 3006 |
| Image | Custom `confluence-api:latest` |

**Endpoints:**

```
GET  /spaces                         # List spaces
GET  /spaces/{space}/pages           # List pages in space
GET  /pages/{page_id}                # Get page content
GET  /pages/{page_id}/children       # Get child pages
POST /search                         # CQL search
GET  /health                         # Health check
```

---

## Data Sources Configuration

### Configuration Model

Organizations configure which data sources to index through the Dashboard UI. Configuration is stored in PostgreSQL.

**Source Types:**

| Source | Filter Type | Example |
|--------|-------------|---------|
| GitHub Repos | Glob patterns, topics, org | `user/*-api`, `topic:backend` |
| Jira Tickets | JQL query | `project = ENG AND labels = bug` |
| Confluence | Space keys, labels | `spaces: [ENG, ARCH]` |

### Filter Syntax

**GitHub Repository Filters:**

```yaml
github:
  # Include patterns (glob syntax)
  include:
    - "myorg/*"              # All repos in org
    - "myorg/backend-*"      # Repos starting with backend-
    - "topic:microservices"  # Repos with topic
    - "language:python"      # Python repos only

  # Exclude patterns
  exclude:
    - "myorg/*-deprecated"
    - "myorg/archive-*"

  # Branch filter (default: main/master)
  branches:
    - "main"
    - "develop"

  # File patterns to index
  file_patterns:
    - "**/*.py"
    - "**/*.ts"
    - "**/*.go"
    - "!**/node_modules/**"
    - "!**/__pycache__/**"
```

**Jira Ticket Filters:**

```yaml
jira:
  # JQL query
  jql: |
    project IN (ENG, PLATFORM)
    AND status != Closed
    AND created >= -90d

  # Issue types to include
  issue_types:
    - Bug
    - Story
    - Task

  # Labels filter (optional)
  labels:
    include:
      - backend
      - api
    exclude:
      - wontfix

  # Max results per sync
  max_results: 1000
```

**Confluence Filters:**

```yaml
confluence:
  # Spaces to index
  spaces:
    - key: ENG
      include_children: true
      labels: ["architecture", "api"]
    - key: PLATFORM
      root_pages:
        - "System Design"
        - "API Documentation"

  # Global label filter
  labels:
    include:
      - technical
      - engineering
    exclude:
      - draft
      - archived

  # Content types
  content_types:
    - page
    - blogpost
```

---

## Database Schema Extensions

### New Tables

```sql
-- Organization configuration
CREATE TABLE organizations (
    org_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    settings_json TEXT DEFAULT '{}'
);

-- Data source configurations
CREATE TABLE data_sources (
    source_id VARCHAR(255) PRIMARY KEY,
    org_id VARCHAR(255) NOT NULL REFERENCES organizations(org_id),
    source_type VARCHAR(50) NOT NULL,  -- github, jira, confluence
    name VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    config_json TEXT NOT NULL,  -- JSON filter configuration
    last_sync_at TIMESTAMP,
    last_sync_status VARCHAR(50),  -- success, failed, in_progress
    last_sync_stats_json TEXT DEFAULT '{}',  -- items indexed, errors, duration
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,

    UNIQUE(org_id, source_type, name)
);

-- Indexing jobs
CREATE TABLE indexing_jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    org_id VARCHAR(255) NOT NULL REFERENCES organizations(org_id),
    source_id VARCHAR(255) REFERENCES data_sources(source_id),
    job_type VARCHAR(50) NOT NULL,  -- full, incremental, delete
    status VARCHAR(50) NOT NULL,  -- queued, running, completed, failed
    progress_percent INTEGER DEFAULT 0,
    items_total INTEGER DEFAULT 0,
    items_processed INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata_json TEXT DEFAULT '{}'
);

-- Indexed items tracking
CREATE TABLE indexed_items (
    item_id VARCHAR(255) PRIMARY KEY,
    org_id VARCHAR(255) NOT NULL,
    source_id VARCHAR(255) NOT NULL REFERENCES data_sources(source_id),
    source_type VARCHAR(50) NOT NULL,
    external_id VARCHAR(500) NOT NULL,  -- repo/file path, ticket key, page id
    collection VARCHAR(100) NOT NULL,  -- chromadb collection name
    chunk_count INTEGER DEFAULT 1,
    last_indexed_at TIMESTAMP NOT NULL,
    content_hash VARCHAR(64),  -- For change detection
    metadata_json TEXT DEFAULT '{}',

    UNIQUE(org_id, source_type, external_id)
);

-- Index for efficient queries
CREATE INDEX idx_data_sources_org ON data_sources(org_id);
CREATE INDEX idx_data_sources_type ON data_sources(source_type);
CREATE INDEX idx_indexing_jobs_org ON indexing_jobs(org_id);
CREATE INDEX idx_indexing_jobs_status ON indexing_jobs(status);
CREATE INDEX idx_indexed_items_org ON indexed_items(org_id);
CREATE INDEX idx_indexed_items_source ON indexed_items(source_id);
```

### SQLAlchemy Models

```python
# dashboard-api/core/database/knowledge_models.py

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from .models import Base, utc_now


class OrganizationDB(Base):
    __tablename__ = "organizations"

    org_id = Column(String(255), primary_key=True)
    name = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    settings_json = Column(Text, default="{}")

    data_sources = relationship("DataSourceDB", back_populates="organization")


class DataSourceDB(Base):
    __tablename__ = "data_sources"

    source_id = Column(String(255), primary_key=True)
    org_id = Column(String(255), ForeignKey("organizations.org_id"), nullable=False)
    source_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True)
    config_json = Column(Text, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)
    last_sync_stats_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    created_by = Column(String(255), nullable=False)

    organization = relationship("OrganizationDB", back_populates="data_sources")
    indexed_items = relationship("IndexedItemDB", back_populates="data_source")


class IndexingJobDB(Base):
    __tablename__ = "indexing_jobs"

    job_id = Column(String(255), primary_key=True)
    org_id = Column(String(255), ForeignKey("organizations.org_id"), nullable=False)
    source_id = Column(String(255), ForeignKey("data_sources.source_id"), nullable=True)
    job_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    progress_percent = Column(Integer, default=0)
    items_total = Column(Integer, default=0)
    items_processed = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    metadata_json = Column(Text, default="{}")


class IndexedItemDB(Base):
    __tablename__ = "indexed_items"

    item_id = Column(String(255), primary_key=True)
    org_id = Column(String(255), nullable=False)
    source_id = Column(String(255), ForeignKey("data_sources.source_id"), nullable=False)
    source_type = Column(String(50), nullable=False)
    external_id = Column(String(500), nullable=False)
    collection = Column(String(100), nullable=False)
    chunk_count = Column(Integer, default=1)
    last_indexed_at = Column(DateTime, nullable=False)
    content_hash = Column(String(64), nullable=True)
    metadata_json = Column(Text, default="{}")

    data_source = relationship("DataSourceDB", back_populates="indexed_items")
```

---

## MCP Server Implementations

### LlamaIndex MCP Server

```python
# mcp-servers/llamaindex-mcp/llamaindex_mcp.py

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
import httpx

mcp = FastMCP("llamaindex")

LLAMAINDEX_URL = "http://llamaindex-service:8002"


class QueryRequest(BaseModel):
    query: str
    org_id: str
    source_types: list[str] | None = None  # ["code", "jira", "confluence"]
    top_k: int = 10
    include_metadata: bool = True


class QueryResult(BaseModel):
    content: str
    source_type: str
    source_id: str
    relevance_score: float
    metadata: dict


@mcp.tool()
async def knowledge_query(
    query: str,
    org_id: str,
    source_types: str = "code,jira,confluence",
    top_k: int = 10
) -> str:
    """
    Query the knowledge base using hybrid search (vectors + graph).

    Args:
        query: Natural language query
        org_id: Organization ID to scope the search
        source_types: Comma-separated list of sources (code, jira, confluence)
        top_k: Number of results to return

    Returns:
        Formatted search results with context
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LLAMAINDEX_URL}/query",
            json={
                "query": query,
                "org_id": org_id,
                "source_types": source_types.split(","),
                "top_k": top_k,
                "include_metadata": True
            },
            timeout=60.0
        )
        response.raise_for_status()
        results = response.json()

    # Format results for Claude
    formatted = []
    for i, result in enumerate(results["results"], 1):
        formatted.append(f"""
### Result {i} ({result['source_type']}) - Score: {result['relevance_score']:.3f}
**Source:** {result['source_id']}
```
{result['content'][:2000]}
```
""")

    return "\n".join(formatted) if formatted else "No relevant results found."


@mcp.tool()
async def code_search(
    query: str,
    org_id: str,
    repo_filter: str = "*",
    language: str = "*",
    top_k: int = 10
) -> str:
    """
    Search code across indexed repositories.

    Args:
        query: Code or natural language query
        org_id: Organization ID
        repo_filter: Repository glob pattern (e.g., "backend-*")
        language: Programming language filter
        top_k: Number of results

    Returns:
        Relevant code snippets with file paths
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LLAMAINDEX_URL}/query/code",
            json={
                "query": query,
                "org_id": org_id,
                "filters": {
                    "repo": repo_filter,
                    "language": language
                },
                "top_k": top_k
            },
            timeout=60.0
        )
        response.raise_for_status()
        results = response.json()

    formatted = []
    for result in results["results"]:
        meta = result["metadata"]
        formatted.append(f"""
**{meta['repo']}/{meta['file_path']}** (lines {meta['line_start']}-{meta['line_end']})
```{meta['language']}
{result['content']}
```
""")

    return "\n".join(formatted) if formatted else "No code matches found."


@mcp.tool()
async def find_related_code(
    entity: str,
    entity_type: str,
    org_id: str,
    relationship: str = "all"
) -> str:
    """
    Find code related to a specific entity using the knowledge graph.

    Args:
        entity: Entity name (function, class, module)
        entity_type: Type of entity (function, class, module, file)
        org_id: Organization ID
        relationship: Relationship type (calls, imports, extends, all)

    Returns:
        Related code entities with relationship context
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LLAMAINDEX_URL}/graph/related",
            json={
                "entity": entity,
                "entity_type": entity_type,
                "org_id": org_id,
                "relationship": relationship
            },
            timeout=30.0
        )
        response.raise_for_status()
        results = response.json()

    formatted = ["## Related Code Entities\n"]
    for rel_type, entities in results["relationships"].items():
        formatted.append(f"\n### {rel_type.upper()}\n")
        for entity in entities:
            formatted.append(f"- `{entity['name']}` in {entity['file']} (line {entity['line']})")

    return "\n".join(formatted)


@mcp.tool()
async def search_jira_tickets(
    query: str,
    org_id: str,
    project: str = "*",
    status: str = "*",
    top_k: int = 10
) -> str:
    """
    Search Jira tickets using semantic search.

    Args:
        query: Natural language query
        org_id: Organization ID
        project: Project key filter
        status: Status filter (Open, In Progress, Done, *)
        top_k: Number of results

    Returns:
        Relevant Jira tickets with summaries
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LLAMAINDEX_URL}/query/tickets",
            json={
                "query": query,
                "org_id": org_id,
                "filters": {
                    "project": project,
                    "status": status
                },
                "top_k": top_k
            },
            timeout=30.0
        )
        response.raise_for_status()
        results = response.json()

    formatted = []
    for result in results["results"]:
        meta = result["metadata"]
        formatted.append(f"""
**[{meta['key']}] {meta['summary']}**
- Status: {meta['status']} | Priority: {meta['priority']}
- Labels: {', '.join(meta.get('labels', []))}

{result['content'][:500]}...
""")

    return "\n".join(formatted) if formatted else "No matching tickets found."


@mcp.tool()
async def search_confluence(
    query: str,
    org_id: str,
    space: str = "*",
    top_k: int = 10
) -> str:
    """
    Search Confluence documentation.

    Args:
        query: Natural language query
        org_id: Organization ID
        space: Space key filter
        top_k: Number of results

    Returns:
        Relevant documentation excerpts
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LLAMAINDEX_URL}/query/docs",
            json={
                "query": query,
                "org_id": org_id,
                "filters": {"space": space},
                "top_k": top_k
            },
            timeout=30.0
        )
        response.raise_for_status()
        results = response.json()

    formatted = []
    for result in results["results"]:
        meta = result["metadata"]
        formatted.append(f"""
**{meta['page_title']}** ({meta['space']})
Last updated: {meta['last_modified']}

{result['content'][:1000]}...
""")

    return "\n".join(formatted) if formatted else "No documentation found."
```

### GKG MCP Server

```python
# mcp-servers/gkg-mcp/gkg_mcp.py

from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("gkg")

GKG_URL = "http://gkg-service:8003"


@mcp.tool()
async def analyze_dependencies(
    file_path: str,
    org_id: str,
    repo: str,
    depth: int = 3
) -> str:
    """
    Analyze dependencies of a file or module.

    Args:
        file_path: Path to the file
        org_id: Organization ID
        repo: Repository name
        depth: How deep to traverse dependencies

    Returns:
        Dependency tree with explanations
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GKG_URL}/analyze/dependencies",
            json={
                "file_path": file_path,
                "org_id": org_id,
                "repo": repo,
                "depth": depth
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()["formatted_output"]


@mcp.tool()
async def find_usages(
    symbol: str,
    org_id: str,
    repo: str = "*"
) -> str:
    """
    Find all usages of a symbol (function, class, variable).

    Args:
        symbol: Symbol name to search for
        org_id: Organization ID
        repo: Repository filter

    Returns:
        List of files and locations where the symbol is used
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GKG_URL}/query/usages",
            json={
                "symbol": symbol,
                "org_id": org_id,
                "repo": repo
            },
            timeout=30.0
        )
        response.raise_for_status()
        results = response.json()

    formatted = [f"## Usages of `{symbol}`\n"]
    for usage in results["usages"]:
        formatted.append(f"- {usage['file']}:{usage['line']} ({usage['context']})")

    return "\n".join(formatted)


@mcp.tool()
async def get_call_graph(
    function_name: str,
    org_id: str,
    repo: str,
    direction: str = "both",
    depth: int = 2
) -> str:
    """
    Get the call graph for a function.

    Args:
        function_name: Function name
        org_id: Organization ID
        repo: Repository name
        direction: "callers", "callees", or "both"
        depth: Traversal depth

    Returns:
        Call graph visualization
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GKG_URL}/graph/calls",
            json={
                "function_name": function_name,
                "org_id": org_id,
                "repo": repo,
                "direction": direction,
                "depth": depth
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()["formatted_graph"]


@mcp.tool()
async def get_class_hierarchy(
    class_name: str,
    org_id: str,
    repo: str = "*"
) -> str:
    """
    Get inheritance hierarchy for a class.

    Args:
        class_name: Class name
        org_id: Organization ID
        repo: Repository filter

    Returns:
        Class hierarchy diagram
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GKG_URL}/graph/hierarchy",
            json={
                "class_name": class_name,
                "org_id": org_id,
                "repo": repo
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()["formatted_hierarchy"]
```

---

## Dashboard UI Extensions

### New UI Components

The External Dashboard (:3005) needs new components for managing data sources.

**New Routes:**

```
/settings/sources           # Data sources overview
/settings/sources/github    # GitHub repository configuration
/settings/sources/jira      # Jira project configuration
/settings/sources/confluence # Confluence space configuration
/settings/indexing          # Indexing jobs & status
```

### React Components Structure

```
external-dashboard/src/
├── pages/
│   └── settings/
│       ├── SourcesPage.tsx           # Main sources management
│       ├── GitHubSourcesPage.tsx     # GitHub config UI
│       ├── JiraSourcesPage.tsx       # Jira config UI
│       ├── ConfluenceSourcesPage.tsx # Confluence config UI
│       └── IndexingPage.tsx          # Indexing jobs monitor
│
├── components/
│   └── sources/
│       ├── SourceCard.tsx            # Source status card
│       ├── SourceForm.tsx            # Generic source form
│       ├── GitHubRepoSelector.tsx    # GitHub repo picker
│       ├── JiraProjectSelector.tsx   # Jira project picker
│       ├── ConfluenceSpaceSelector.tsx # Confluence space picker
│       ├── FilterBuilder.tsx         # Visual filter builder
│       ├── IndexingProgress.tsx      # Progress indicator
│       └── SyncButton.tsx            # Trigger sync button
│
└── hooks/
    └── useSources.ts                 # Data sources API hooks
```

### UI Wireframes

**Sources Overview Page:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Knowledge Sources                                    [+ Add]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ 🐙 GitHub           │  │ 📋 Jira             │              │
│  │ 12 repositories     │  │ 3 projects          │              │
│  │ Last sync: 2h ago   │  │ Last sync: 1h ago   │              │
│  │ ✅ Healthy          │  │ ✅ Healthy          │              │
│  │ [Configure] [Sync]  │  │ [Configure] [Sync]  │              │
│  └─────────────────────┘  └─────────────────────┘              │
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ 📄 Confluence       │  │ 📊 Indexing Status  │              │
│  │ 2 spaces            │  │ 156,234 vectors     │              │
│  │ Last sync: 30m ago  │  │ 45,678 graph nodes  │              │
│  │ ✅ Healthy          │  │ 892 MB storage      │              │
│  │ [Configure] [Sync]  │  │ [View Jobs]         │              │
│  └─────────────────────┘  └─────────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**GitHub Configuration Page:**

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Repository Sources                          [Save]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Organization: [acme-corp        ▼]                             │
│                                                                 │
│  ┌─ Include Patterns ──────────────────────────────────────┐   │
│  │ [x] All repositories     [ ] By pattern                 │   │
│  │                                                          │   │
│  │ Patterns:                                                │   │
│  │ ┌────────────────────────────────────────────┐          │   │
│  │ │ acme-corp/backend-*                    [x] │          │   │
│  │ │ acme-corp/frontend-*                   [x] │          │   │
│  │ │ + Add pattern                              │          │   │
│  │ └────────────────────────────────────────────┘          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Filters ───────────────────────────────────────────────┐   │
│  │ Topics:     [backend] [api] [microservice] [+ Add]      │   │
│  │ Languages:  [Python ▼] [TypeScript ▼] [Go ▼]            │   │
│  │ Visibility: [x] Public  [x] Private  [ ] Internal       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Exclude Patterns ──────────────────────────────────────┐   │
│  │ │ *-deprecated                               [x] │       │   │
│  │ │ archive-*                                  [x] │       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ File Indexing ─────────────────────────────────────────┐   │
│  │ Include: **/*.py, **/*.ts, **/*.go, **/*.md             │   │
│  │ Exclude: **/node_modules/**, **/__pycache__/**          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Preview: 12 repositories will be indexed                       │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ ☑ acme-corp/backend-api          Python   2.3 MB       │    │
│  │ ☑ acme-corp/backend-auth         Python   890 KB       │    │
│  │ ☑ acme-corp/frontend-web         TypeScript 4.1 MB     │    │
│  │ ...                                                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Indexing Pipeline

### Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           INDEXING PIPELINE                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TRIGGER                                                                     │
│  ├─ UI: "Sync Now" button                                                    │
│  ├─ Webhook: GitHub push event                                               │
│  ├─ Webhook: Jira ticket update                                              │
│  ├─ Webhook: Confluence page edit                                            │
│  └─ Scheduled: Cron job (daily full, hourly incremental)                     │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      INDEXER WORKER                                  │    │
│  │                                                                      │    │
│  │  1. FETCH CONFIGURATION                                              │    │
│  │     └─ Load data_sources from PostgreSQL                             │    │
│  │     └─ Parse filter configurations                                   │    │
│  │                                                                      │    │
│  │  2. SOURCE FETCHING (parallel by source type)                        │    │
│  │     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │    │
│  │     │ GitHub      │  │ Jira        │  │ Confluence  │              │    │
│  │     │ ├─ Clone    │  │ ├─ JQL      │  │ ├─ Fetch    │              │    │
│  │     │ │  repos    │  │ │  search   │  │ │  pages    │              │    │
│  │     │ └─ Filter   │  │ └─ Paginate │  │ └─ Parse    │              │    │
│  │     │    files    │  │             │  │    content  │              │    │
│  │     └─────────────┘  └─────────────┘  └─────────────┘              │    │
│  │                                                                      │    │
│  │  3. PROCESSING (parallel)                                            │    │
│  │     ┌─────────────────────────────────────────────────────────┐     │    │
│  │     │ Code Processing                                          │     │    │
│  │     │ ├─ Parse AST (tree-sitter)                               │     │    │
│  │     │ ├─ Extract entities (functions, classes)                 │     │    │
│  │     │ ├─ Chunk by semantic units                               │     │    │
│  │     │ └─ Generate embeddings                                   │     │    │
│  │     └─────────────────────────────────────────────────────────┘     │    │
│  │     ┌─────────────────────────────────────────────────────────┐     │    │
│  │     │ Document Processing                                      │     │    │
│  │     │ ├─ Parse HTML/Markdown                                   │     │    │
│  │     │ ├─ Extract sections                                      │     │    │
│  │     │ ├─ Chunk with overlap                                    │     │    │
│  │     │ └─ Generate embeddings                                   │     │    │
│  │     └─────────────────────────────────────────────────────────┘     │    │
│  │                                                                      │    │
│  │  4. STORAGE (parallel to different stores)                           │    │
│  │     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │    │
│  │     │ ChromaDB    │  │ GKG         │  │ PostgreSQL  │              │    │
│  │     │ └─ Upsert   │  │ └─ Index    │  │ └─ Track    │              │    │
│  │     │    vectors  │  │    graph    │  │    items    │              │    │
│  │     └─────────────┘  └─────────────┘  └─────────────┘              │    │
│  │                                                                      │    │
│  │  5. REPORTING                                                        │    │
│  │     └─ Update job status                                             │    │
│  │     └─ Publish progress to Redis                                     │    │
│  │     └─ Send completion notification                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Incremental Indexing

For efficiency, the indexer tracks content hashes and only reindexes changed content:

```python
# indexer-worker/incremental.py

async def should_reindex(item_id: str, new_content_hash: str, db: AsyncSession) -> bool:
    """Check if content needs reindexing."""
    result = await db.execute(
        select(IndexedItemDB.content_hash)
        .where(IndexedItemDB.item_id == item_id)
    )
    existing_hash = result.scalar_one_or_none()
    return existing_hash != new_content_hash


async def incremental_index_repo(repo: str, org_id: str, source_id: str):
    """Incrementally index only changed files in a repository."""
    # Get list of changed files since last index
    last_indexed = await get_last_indexed_commit(repo, org_id)
    changed_files = await get_changed_files(repo, last_indexed)

    for file_path in changed_files:
        content = await read_file(repo, file_path)
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        if await should_reindex(f"{repo}:{file_path}", content_hash, db):
            await index_file(repo, file_path, content, org_id, source_id)
```

---

## Query Flow Architecture

### Hybrid Query Engine

The LlamaIndex service orchestrates queries across ChromaDB (vectors) and GKG (graph):

```python
# llamaindex-service/query_engine.py

from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer


class HybridQueryEngine:
    """Combines vector search with graph traversal."""

    def __init__(self, chroma_client, gkg_client, config: QueryConfig):
        self.chroma = chroma_client
        self.gkg = gkg_client
        self.config = config

    async def query(self, query: str, org_id: str, source_types: list[str]) -> QueryResponse:
        """Execute hybrid query across multiple sources."""

        # 1. Vector search in ChromaDB
        vector_results = await self._vector_search(query, org_id, source_types)

        # 2. If code-related, enrich with graph context
        if "code" in source_types:
            graph_context = await self._graph_enrichment(query, vector_results)
            vector_results = self._merge_graph_context(vector_results, graph_context)

        # 3. Rerank results
        reranked = await self._rerank(query, vector_results)

        # 4. Assemble context
        return self._assemble_response(reranked)

    async def _vector_search(
        self,
        query: str,
        org_id: str,
        source_types: list[str]
    ) -> list[SearchResult]:
        """Search vectors in ChromaDB with org filtering."""
        results = []

        for source_type in source_types:
            collection = self._get_collection(source_type)

            # Query with metadata filter
            search_results = collection.query(
                query_texts=[query],
                n_results=self.config.top_k,
                where={"org_id": org_id}
            )

            results.extend(self._format_results(search_results, source_type))

        return results

    async def _graph_enrichment(
        self,
        query: str,
        vector_results: list[SearchResult]
    ) -> GraphContext:
        """Use GKG to find related code entities."""
        # Extract entities from vector results
        entities = self._extract_entities(vector_results)

        # Query GKG for relationships
        graph_context = await self.gkg.get_related_entities(
            entities=entities,
            relationship_types=["calls", "imports", "extends"],
            depth=2
        )

        return graph_context

    async def _rerank(
        self,
        query: str,
        results: list[SearchResult]
    ) -> list[SearchResult]:
        """Cross-encoder reranking for better relevance."""
        if len(results) <= self.config.rerank_threshold:
            return results

        # Use cross-encoder model
        scores = self.reranker.score(
            query,
            [r.content for r in results]
        )

        # Sort by new scores
        ranked = sorted(
            zip(results, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [r for r, _ in ranked[:self.config.top_k]]
```

### Query Routing

```python
# llamaindex-service/router.py

class QueryRouter:
    """Routes queries to appropriate indexes based on intent."""

    INTENT_PATTERNS = {
        "code": [
            r"function\s+\w+",
            r"class\s+\w+",
            r"how\s+(does|is|to)\s+.*implemented",
            r"where\s+is\s+.*defined",
            r"find\s+(the\s+)?(code|function|class)",
        ],
        "docs": [
            r"documentation",
            r"how\s+to\s+use",
            r"architecture",
            r"design\s+doc",
            r"explain\s+the\s+system",
        ],
        "tickets": [
            r"bug",
            r"issue",
            r"ticket",
            r"JIRA",
            r"\b[A-Z]+-\d+\b",  # PROJ-123 pattern
        ]
    }

    def route(self, query: str) -> list[str]:
        """Determine which indexes to query."""
        matched_types = []

        for source_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    matched_types.append(source_type)
                    break

        # Default to all if no specific intent detected
        return matched_types if matched_types else ["code", "docs", "tickets"]
```

---

## Docker Services Configuration

### docker-compose.knowledge.yml

```yaml
version: '3.8'

services:
  # =============================================================================
  # CHROMADB - Vector Database
  # =============================================================================
  chromadb:
    image: chromadb/chroma:0.4.22
    container_name: agent-chromadb
    ports:
      - "8001:8000"
    volumes:
      - chromadb_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
      - ALLOW_RESET=FALSE
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - agent-network
    restart: unless-stopped

  # =============================================================================
  # LLAMAINDEX SERVICE - Hybrid RAG Orchestration
  # =============================================================================
  llamaindex-service:
    build:
      context: ./llamaindex-service
      dockerfile: Dockerfile
    container_name: agent-llamaindex
    ports:
      - "8002:8002"
    environment:
      - CHROMADB_URL=http://chromadb:8000
      - GKG_URL=http://gkg-service:8003
      - REDIS_URL=redis://redis:6379/0
      - POSTGRES_URL=${DATABASE_URL}
      - EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
      - RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
      - LOG_LEVEL=INFO
    depends_on:
      chromadb:
        condition: service_healthy
      gkg-service:
        condition: service_started
      redis:
        condition: service_started
    volumes:
      - llama_cache:/app/cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - agent-network
    restart: unless-stopped

  # =============================================================================
  # LLAMAINDEX MCP SERVER - Tool Interface
  # =============================================================================
  llamaindex-mcp:
    build:
      context: ./mcp-servers/llamaindex-mcp
      dockerfile: Dockerfile
    container_name: agent-llamaindex-mcp
    ports:
      - "9006:9006"
    environment:
      - LLAMAINDEX_URL=http://llamaindex-service:8002
      - MCP_PORT=9006
    depends_on:
      - llamaindex-service
    networks:
      - agent-network
    restart: unless-stopped

  # =============================================================================
  # GKG SERVICE - GitLab Knowledge Graph
  # =============================================================================
  gkg-service:
    build:
      context: ./gkg-service
      dockerfile: Dockerfile
    container_name: agent-gkg
    ports:
      - "8003:8003"
    environment:
      - DATA_DIR=/data/gkg
      - REPOS_DIR=/data/repos
      - LOG_LEVEL=info
    volumes:
      - gkg_data:/data/gkg
      - repos_data:/data/repos:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - agent-network
    restart: unless-stopped

  # =============================================================================
  # GKG MCP SERVER - Tool Interface
  # =============================================================================
  gkg-mcp:
    build:
      context: ./mcp-servers/gkg-mcp
      dockerfile: Dockerfile
    container_name: agent-gkg-mcp
    ports:
      - "9007:9007"
    environment:
      - GKG_URL=http://gkg-service:8003
      - MCP_PORT=9007
    depends_on:
      - gkg-service
    networks:
      - agent-network
    restart: unless-stopped

  # =============================================================================
  # INDEXER WORKER - Background Indexing Service
  # =============================================================================
  indexer-worker:
    build:
      context: ./indexer-worker
      dockerfile: Dockerfile
    container_name: agent-indexer
    ports:
      - "8004:8004"
    environment:
      - CHROMADB_URL=http://chromadb:8000
      - GKG_URL=http://gkg-service:8003
      - REDIS_URL=redis://redis:6379/0
      - POSTGRES_URL=${DATABASE_URL}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - JIRA_URL=${JIRA_URL}
      - JIRA_EMAIL=${JIRA_EMAIL}
      - JIRA_API_TOKEN=${JIRA_API_TOKEN}
      - CONFLUENCE_URL=${CONFLUENCE_URL}
      - CONFLUENCE_EMAIL=${CONFLUENCE_EMAIL}
      - CONFLUENCE_API_TOKEN=${CONFLUENCE_API_TOKEN}
      - EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
      - REPOS_DIR=/data/repos
      - LOG_LEVEL=INFO
    depends_on:
      - chromadb
      - gkg-service
      - redis
      - postgres
    volumes:
      - repos_data:/data/repos
      - indexer_cache:/app/cache
    networks:
      - agent-network
    restart: unless-stopped

  # =============================================================================
  # CONFLUENCE API SERVICE - Credential Isolation
  # =============================================================================
  confluence-api:
    build:
      context: ./api-services/confluence-api
      dockerfile: Dockerfile
    container_name: agent-confluence-api
    ports:
      - "3006:3006"
    environment:
      - CONFLUENCE_URL=${CONFLUENCE_URL}
      - CONFLUENCE_EMAIL=${CONFLUENCE_EMAIL}
      - CONFLUENCE_API_TOKEN=${CONFLUENCE_API_TOKEN}
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3006/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - agent-network
    restart: unless-stopped

volumes:
  chromadb_data:
    driver: local
  gkg_data:
    driver: local
  repos_data:
    driver: local
  llama_cache:
    driver: local
  indexer_cache:
    driver: local

networks:
  agent-network:
    external: true
```

### Service Dockerfiles

**LlamaIndex Service:**

```dockerfile
# llamaindex-service/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create cache directory
RUN mkdir -p /app/cache

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
```

**GKG Service:**

```dockerfile
# gkg-service/Dockerfile
FROM rust:1.75-slim AS builder

WORKDIR /build

# Install GKG binary
RUN curl -fsSL https://gitlab.com/gitlab-org/rust/knowledge-graph/-/raw/main/install.sh | bash

FROM debian:bookworm-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy GKG binary
COPY --from=builder /root/.cargo/bin/gkg /usr/local/bin/gkg

# Copy wrapper application
COPY . .

# Create data directories
RUN mkdir -p /data/gkg /data/repos

EXPOSE 8003

CMD ["python3", "server.py"]
```

**Indexer Worker:**

```dockerfile
# indexer-worker/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /data/repos /app/cache

EXPOSE 8004

CMD ["python", "worker.py"]
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1-2)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 1.1 | Set up ChromaDB service | `docker-compose.knowledge.yml` |
| 1.2 | Create database migrations | New tables in PostgreSQL |
| 1.3 | Implement Dashboard API endpoints | CRUD for data_sources |
| 1.4 | Create basic UI components | Sources management page |

### Phase 2: LlamaIndex Integration (Week 3-4)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 2.1 | Build LlamaIndex service | Vector search + embedding |
| 2.2 | Implement LlamaIndex MCP server | MCP tool definitions |
| 2.3 | Create query engine | Hybrid search logic |
| 2.4 | Integrate with agent-engine | Update mcp.json |

### Phase 3: GKG Integration (Week 5-6)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 3.1 | Build GKG service wrapper | HTTP API for GKG CLI |
| 3.2 | Implement GKG MCP server | Graph query tools |
| 3.3 | Create graph-enriched queries | LlamaIndex + GKG fusion |
| 3.4 | Add call graph visualization | Dashboard component |

### Phase 4: Indexing Pipeline (Week 7-8)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 4.1 | Build indexer worker | Background job processor |
| 4.2 | Implement GitHub indexing | Clone, parse, embed repos |
| 4.3 | Implement Jira indexing | Fetch and embed tickets |
| 4.4 | Implement Confluence indexing | Fetch and embed pages |

### Phase 5: Dashboard UI (Week 9-10)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 5.1 | GitHub source configuration | Repo selector + filters |
| 5.2 | Jira source configuration | Project/JQL builder |
| 5.3 | Confluence source configuration | Space selector |
| 5.4 | Indexing jobs monitor | Progress + logs UI |

### Phase 6: Testing & Polish (Week 11-12)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 6.1 | Integration tests | End-to-end test suite |
| 6.2 | Performance optimization | Query caching, batch indexing |
| 6.3 | Documentation | User guide, API docs |
| 6.4 | Production hardening | Error handling, monitoring |

---

## Security Considerations

### Credential Isolation

```
┌──────────────────────────────────────────────────────────────────┐
│                    CREDENTIAL ISOLATION                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MCP SERVERS (No Credentials)     API SERVICES (With Credentials)│
│  ┌─────────────────────┐          ┌─────────────────────┐       │
│  │ LlamaIndex MCP      │─────────▶│ LlamaIndex Service  │       │
│  │ (Tools only)        │          │ (Internal calls)    │       │
│  └─────────────────────┘          └─────────────────────┘       │
│                                              │                   │
│  ┌─────────────────────┐          ┌─────────▼─────────┐        │
│  │ GKG MCP             │─────────▶│ GKG Service       │        │
│  │ (Tools only)        │          │ (Local graph DB)  │        │
│  └─────────────────────┘          └───────────────────┘        │
│                                              │                   │
│                                   ┌──────────▼─────────┐        │
│                                   │ Indexer Worker     │        │
│                                   │ ├─ GITHUB_TOKEN    │        │
│                                   │ ├─ JIRA_API_TOKEN  │        │
│                                   │ └─ CONFLUENCE_TOKEN│        │
│                                   └────────────────────┘        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Data Access Control

- **Organization Isolation:** All queries filtered by `org_id`
- **Source Filtering:** Only index configured sources
- **API Token Scoping:** Use read-only tokens where possible
- **Audit Logging:** Track all indexing operations

### Network Security

- All services on internal Docker network
- Only API Gateway exposed externally
- MCP servers accessible only to agent-engine
- TLS for external API calls

---

## Agent Skill Integration

### Updated mcp.json

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"}
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
    },
    "llamaindex": {
      "url": "http://llamaindex-mcp:9006/sse",
      "transport": "sse"
    },
    "gkg": {
      "url": "http://gkg-mcp:9007/sse",
      "transport": "sse"
    }
  }
}
```

### New Skill: knowledge-query

```markdown
# Knowledge Query Skill

## Purpose
Query the organization's knowledge base for relevant context.

## When to Use
- Before implementing code changes (find similar implementations)
- When analyzing bugs (find related tickets and documentation)
- When understanding system architecture (query documentation)
- When finding dependencies and call graphs (use GKG)

## Tools Available
- `llamaindex:knowledge_query` - Hybrid search across all sources
- `llamaindex:code_search` - Search code specifically
- `llamaindex:search_jira_tickets` - Search Jira tickets
- `llamaindex:search_confluence` - Search documentation
- `llamaindex:find_related_code` - Find related code via graph
- `gkg:analyze_dependencies` - Analyze file dependencies
- `gkg:find_usages` - Find symbol usages
- `gkg:get_call_graph` - Get function call graph

## Workflow
1. Identify the query intent (code, docs, tickets, or hybrid)
2. Use appropriate tool based on intent
3. Analyze results for relevance
4. Extract actionable context for the task
```

---

## Summary

This architecture provides:

1. **Modularity:** Each component is a separate Docker service
2. **Configurability:** UI-driven source management with flexible filters
3. **Scalability:** Horizontal scaling of indexer workers
4. **Multi-tenancy:** Organization-based data isolation
5. **Hybrid Search:** Combines vectors (ChromaDB) with graphs (GKG)
6. **Real-time Updates:** Webhook-triggered incremental indexing
7. **Security:** Credential isolation and network segmentation

The system integrates seamlessly with the existing Agent Bot architecture while adding powerful knowledge retrieval capabilities for the Claude Code CLI agents.
