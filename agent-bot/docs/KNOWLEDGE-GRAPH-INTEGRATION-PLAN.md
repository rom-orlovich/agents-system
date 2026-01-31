# Knowledge Graph Integration Plan for Agent-Engine Discovery

## Overview

This document describes how the agent-engine integrates with the GitLab Knowledge Graph (gkg) for enhanced code discovery and navigation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent Engine                                  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐    │
│  │ Brain Agent │───▶│Planning Agent│───▶│  Discovery Skill    │    │
│  └─────────────┘    └──────────────┘    │                     │    │
│                                          │  - File search      │    │
│                                          │  - Code search      │    │
│                                          │  - Symbol lookup    │    │
│                                          │  - Dependency graph │    │
│                                          └─────────┬───────────┘    │
└────────────────────────────────────────────────────┼────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Knowledge Graph MCP Server (Port 9005)           │
├─────────────────────────────────────────────────────────────────────┤
│  Tools:                                                              │
│  - search_codebase        - find_symbol_references                  │
│  - get_code_structure     - find_dependencies                       │
│  - find_code_path         - get_code_neighbors                      │
│  - get_graph_stats                                                   │
└─────────────────────────────────────────────────────┬───────────────┘
                                                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Knowledge Graph Service (Port 4000)              │
├─────────────────────────────────────────────────────────────────────┤
│  Components:                                                         │
│  ┌──────────────┐    ┌───────────────┐    ┌──────────────────┐     │
│  │   Rust API   │    │  Kuzu Graph   │    │    gkg CLI       │     │
│  │   (Axum)     │◀──▶│   Database    │◀──▶│   (Indexer)      │     │
│  └──────────────┘    └───────────────┘    └──────────────────┘     │
│                                                    ▲                 │
│                                                    │                 │
│                            ┌───────────────────────┘                 │
│                            │                                         │
│                    ┌───────┴────────┐                               │
│                    │  Repo Syncer   │                               │
│                    │  (sync-repos)  │                               │
│                    └───────┬────────┘                               │
└────────────────────────────┼────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Local Repositories                             │
│  /data/repos/                                                        │
│  ├── repo-1/                                                         │
│  ├── repo-2/                                                         │
│  └── repo-n/                                                         │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Repository Indexing

```
Local Repos ──▶ sync-repos.sh ──▶ gkg index ──▶ Kuzu Database
```

The sync script:
1. Pulls latest changes from configured repositories
2. Runs `gkg index` to parse code structure
3. Stores graph data in Kuzu database

### 2. Discovery Query Flow

```
Agent Query ──▶ Discovery Skill ──▶ KG MCP ──▶ KG API ──▶ Kuzu
```

Example flow for "find all usages of function X":
1. Agent sends discovery request
2. Discovery skill calls `find_symbol_references` via MCP
3. MCP server queries Knowledge Graph API
4. API queries Kuzu database
5. Results returned to agent

## Integration Points

### 1. Discovery Skill Enhancement

The `DiscoverySkill` gains new knowledge graph-powered actions:

| Action | Description | KG MCP Tool |
|--------|-------------|-------------|
| `kg_search` | Semantic code search | `search_codebase` |
| `kg_references` | Find symbol usages | `find_symbol_references` |
| `kg_structure` | Get code structure | `get_code_structure` |
| `kg_dependencies` | Get dependency graph | `find_dependencies` |
| `kg_path` | Find relationship path | `find_code_path` |
| `kg_neighbors` | Get related entities | `get_code_neighbors` |

### 2. Planning Agent Integration

The Planning Agent uses the knowledge graph for:
- Understanding codebase architecture before planning
- Identifying affected files and dependencies
- Finding related code patterns for reference

### 3. Executor Agent Integration

The Executor Agent uses the knowledge graph for:
- Locating exact file positions for edits
- Understanding import relationships
- Verifying changes don't break dependencies

## Node Types

| Type | Description | Example |
|------|-------------|---------|
| `file` | Source code file | `src/main.py` |
| `directory` | Directory | `src/utils/` |
| `module` | Python/JS module | `agent_engine.core` |
| `class` | Class definition | `TaskWorker` |
| `function` | Function/method | `async def run()` |
| `variable` | Global/constant | `MAX_RETRIES = 3` |
| `interface` | Interface/protocol | `CLIProvider` |

## Edge Types

| Type | Description | Example |
|------|-------------|---------|
| `imports` | Import relationship | `A imports B` |
| `calls` | Function call | `A calls B` |
| `inherits` | Inheritance | `A extends B` |
| `contains` | Containment | `File contains Class` |
| `uses` | Usage relationship | `A uses B` |
| `implements` | Implementation | `A implements Interface` |

## API Endpoints

### Knowledge Graph API (Port 4000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/nodes` | GET | List all nodes |
| `/api/v1/nodes` | POST | Create node |
| `/api/v1/nodes/:id` | GET | Get node by ID |
| `/api/v1/edges` | GET | List all edges |
| `/api/v1/edges` | POST | Create edge |
| `/api/v1/query/search` | POST | Search nodes |
| `/api/v1/query/path` | POST | Find path |
| `/api/v1/query/neighbors` | POST | Find neighbors |
| `/api/v1/stats` | GET | Graph statistics |

### MCP Tools (Port 9005)

| Tool | Description |
|------|-------------|
| `search_codebase` | Full-text code search |
| `find_symbol_references` | Find all references to a symbol |
| `get_code_structure` | Get repository structure |
| `find_dependencies` | Get imports/calls |
| `find_code_path` | Find relationship path |
| `get_code_neighbors` | Get related entities |
| `get_graph_stats` | Graph statistics |

## Configuration

### Environment Variables

```bash
# Knowledge Graph Service
PORT=4000
GKG_DATA_DIR=/data/graphs
REPOS_DIR=/data/repos

# MCP Server
KG_PORT=9005
KG_KNOWLEDGE_GRAPH_URL=http://knowledge-graph:4000

# Agent Engine
KNOWLEDGE_GRAPH_URL=http://knowledge-graph:4000
```

### Repository Configuration

Create `/app/config/repos.json`:

```json
{
  "repositories": [
    {
      "url": "https://github.com/org/repo1.git",
      "name": "repo1"
    },
    {
      "url": "https://github.com/org/repo2.git",
      "name": "repo2"
    }
  ]
}
```

Or use environment variable:

```bash
REPO_URLS=https://github.com/org/repo1.git,https://github.com/org/repo2.git
```

## Usage Examples

### 1. Search for a Function

```python
# Via Discovery Skill
result = await discovery_skill.execute(SkillInput(
    action="kg_search",
    parameters={
        "query": "handleAuth",
        "node_types": ["function"],
        "language": "typescript"
    }
))
```

### 2. Find All References

```python
# Find all places where a function is called
result = await discovery_skill.execute(SkillInput(
    action="kg_references",
    parameters={
        "symbol_name": "processPayment"
    }
))
```

### 3. Get Dependencies

```python
# Find what a module imports
result = await discovery_skill.execute(SkillInput(
    action="kg_dependencies",
    parameters={
        "node_id": "uuid-of-module",
        "direction": "outgoing"  # what this uses
    }
))
```

### 4. Find Path Between Entities

```python
# How are two entities related?
result = await discovery_skill.execute(SkillInput(
    action="kg_path",
    parameters={
        "source_id": "uuid-of-caller",
        "target_id": "uuid-of-callee"
    }
))
```

## Cursor CLI Integration

When using Cursor CLI with the knowledge graph:

```bash
# Enable the knowledge-graph MCP server
agent chat --mcp knowledge-graph "Find all usages of the processPayment function"
```

The Cursor CLI will:
1. Connect to the knowledge-graph MCP server via SSE
2. Use the available tools for code discovery
3. Return structured results from the knowledge graph

## Sync Schedule

The repository sync can be triggered:

1. **On startup**: Runs automatically when container starts
2. **Scheduled**: Via cron or external scheduler
3. **On-demand**: Via API endpoint `/api/v1/sync`

Recommended schedule for production:
- Every 15 minutes for active development
- Every hour for stable codebases
- On webhook for immediate sync after pushes

## Performance Considerations

- Kuzu database is optimized for graph queries
- Initial indexing may take time for large codebases
- Query results are cached where appropriate
- Use pagination for large result sets

## Monitoring

Monitor the knowledge graph via:

1. **Health endpoint**: `GET /health`
2. **Stats endpoint**: `GET /api/v1/stats`
3. **Logs**: Check sync.log for indexing status
