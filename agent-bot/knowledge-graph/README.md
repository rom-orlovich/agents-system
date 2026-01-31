# Knowledge Graph Service

> Rust-based knowledge graph for code entity relationships and semantic search.

## Purpose

The Knowledge Graph service provides a graph database for storing and querying code entity relationships. It enables semantic code search, dependency tracking, and call graph analysis.

## Architecture

```
Agent Engine / MCP Server
         │
         │ HTTP Request
         ▼
┌─────────────────────────────────────┐
│   Knowledge Graph :4000            │
│                                     │
│  1. Node Management               │
│     - Store code entities          │
│     - Functions, classes, files   │
│                                     │
│  2. Edge Management                │
│     - Store relationships          │
│     - Calls, imports, inherits    │
│                                     │
│  3. Query Operations               │
│     - Path finding                 │
│     - Neighbor queries             │
│     - Semantic search              │
└─────────────────────────────────────┘
```

## Folder Structure

```
knowledge-graph/
├── src/
│   ├── main.rs                 # Application entry point
│   ├── api/
│   │   ├── handlers.rs         # HTTP handlers
│   │   └── mod.rs              # API module
│   ├── models/
│   │   ├── node.rs             # Node model
│   │   ├── edge.rs             # Edge model
│   │   ├── query.rs            # Query models
│   │   └── mod.rs              # Models module
│   └── services/
│       ├── graph.rs             # Graph service logic
│       └── mod.rs               # Services module
├── config/
│   └── repos.json               # Repository configuration
└── Cargo.toml                   # Rust dependencies
```

## Business Logic

### Core Responsibilities

1. **Node Management**: Store code entities (functions, classes, files, etc.)
2. **Edge Management**: Store relationships (calls, imports, inherits, etc.)
3. **Path Finding**: Find paths between entities
4. **Neighbor Queries**: Find related entities
5. **Semantic Search**: Search entities by meaning/context
6. **Graph Statistics**: Provide graph metrics and statistics

## API Endpoints

### Nodes

| Endpoint             | Method | Purpose        |
| -------------------- | ------ | -------------- |
| `/api/v1/nodes`      | GET    | List all nodes |
| `/api/v1/nodes`      | POST   | Create node    |
| `/api/v1/nodes/{id}` | GET    | Get node by ID |
| `/api/v1/nodes/{id}` | DELETE | Delete node    |

### Edges

| Endpoint        | Method | Purpose        |
| --------------- | ------ | -------------- |
| `/api/v1/edges` | GET    | List all edges |
| `/api/v1/edges` | POST   | Create edge    |

### Queries

| Endpoint                  | Method | Purpose                  |
| ------------------------- | ------ | ------------------------ |
| `/api/v1/query/path`      | POST   | Find path between nodes  |
| `/api/v1/query/neighbors` | POST   | Find neighbors of a node |
| `/api/v1/query/search`    | POST   | Search nodes             |

### Statistics

| Endpoint        | Method | Purpose          |
| --------------- | ------ | ---------------- |
| `/api/v1/stats` | GET    | Graph statistics |

## Node Model

```rust
pub struct Node {
    pub id: String,
    pub node_type: NodeType,  // Function, Class, Module, File
    pub name: String,
    pub file_path: String,
    pub metadata: HashMap<String, String>,
}
```

## Edge Model

```rust
pub struct Edge {
    pub id: String,
    pub source: String,        // Source node ID
    pub target: String,        // Target node ID
    pub edge_type: EdgeType,   // Calls, Imports, Inherits, References
    pub metadata: HashMap<String, String>,
}
```

## Usage Examples

### Create Node

```bash
curl -X POST http://localhost:4000/api/v1/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "func:main",
    "node_type": "Function",
    "name": "main",
    "file_path": "src/main.py"
  }'
```

### Create Edge

```bash
curl -X POST http://localhost:4000/api/v1/edges \
  -H "Content-Type: application/json" \
  -d '{
    "source": "func:main",
    "target": "func:helper",
    "edge_type": "Calls"
  }'
```

### Find Path

```bash
curl -X POST http://localhost:4000/api/v1/query/path \
  -H "Content-Type: application/json" \
  -d '{
    "source": "func:main",
    "target": "func:helper",
    "max_depth": 5
  }'
```

## Environment Variables

```bash
PORT=4000
RUST_LOG=debug
REPOS_CONFIG_PATH=/app/config/repos.json
```

## Health Check

```bash
curl http://localhost:4000/health
```

## Building

```bash
cd knowledge-graph
cargo build --release
```

## Related Services

- **agent-engine**: Uses knowledge graph for code discovery
- **mcp-servers/knowledge-graph-mcp**: MCP server wrapper for this service
