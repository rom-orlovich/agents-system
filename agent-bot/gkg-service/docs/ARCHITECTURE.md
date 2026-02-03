# GKG Service Architecture

## Overview

The GKG (GitLab Knowledge Graph) service provides graph-based code analysis capabilities through a REST API. It wraps the GKG CLI binary to enable programmatic access to code relationship queries.

## Design Principles

1. **Protocol-Based Interfaces** - All external dependencies implement typed protocols
2. **Dependency Injection** - Components wired via factory at startup
3. **Behavior-Focused Testing** - Tests verify business behavior, not CLI details
4. **Feature Flags** - Batch operations and caching toggleable via environment

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
│                            (main.py)                             │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Container                           │
│                        (factory.py)                              │
│  ┌─────────────┐                      ┌─────────────┐           │
│  │  Analyzer   │                      │    Cache    │           │
│  └──────┬──────┘                      └──────┬──────┘           │
└─────────┼────────────────────────────────────┼──────────────────┘
          │                                    │
          ▼                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Graph Analyzer Service                        │
│                  (core/graph_analyzer.py)                        │
│                                                                  │
│  • Dependency analysis orchestration                             │
│  • Call graph queries                                            │
│  • Class hierarchy traversal                                     │
│  • Related entities discovery                                    │
│  • Batch operations                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
gkg-service/
├── core/                    # Business logic (framework-agnostic)
│   ├── interfaces.py        # Protocol definitions
│   ├── models.py            # Domain models (Pydantic)
│   └── graph_analyzer.py    # Core orchestration logic
│
├── adapters/                # External service implementations
│   └── gkg_binary_adapter.py  # GKG CLI wrapper
│
├── api/                     # HTTP layer
│   └── routes.py            # FastAPI route handlers
│
├── tests/                   # Behavior-driven tests
│   ├── conftest.py          # Test fixtures and mocks
│   └── test_graph_analyzer_behavior.py
│
├── docs/                    # Documentation
│   └── ARCHITECTURE.md      # This file
│
├── factory.py               # Dependency injection container
├── main.py                  # Application entry point
├── README.md                # Quick start guide
└── CLAUDE.md                # Development guidelines
```

## Protocol Interfaces

### GraphAnalyzerProtocol
Defines code analysis operations:
- `query_dependencies()` - Find file import relationships
- `find_usages()` - Find symbol references
- `get_call_graph()` - Get function call relationships
- `get_class_hierarchy()` - Get inheritance structure
- `get_related_entities()` - Find related code entities
- `index_repo()` - Index repository for queries
- `is_available()` - Check analyzer health
- `get_indexed_count()` - Count indexed repositories

### CacheProtocol
Optional caching for query results:
- `get()` - Retrieve cached value
- `set()` - Store value with TTL
- `delete()` - Remove cached value

## Data Flow

### Query Flow

```
1. Request → API Router → Graph Analyzer Service
2. Service checks cache (if enabled)
3. If miss: Delegate to GraphAnalyzerProtocol implementation
4. GKG Binary Adapter executes CLI command
5. Parse JSON output, build domain models
6. Cache result (if enabled) and return
```

### Supported Query Types

| Query Type | Description | Use Case |
|------------|-------------|----------|
| Dependencies | File import graph | Impact analysis |
| Usages | Symbol references | Refactoring scope |
| Call Graph | Function calls | Debugging paths |
| Hierarchy | Class inheritance | Architecture understanding |
| Related | All relationships | Context building |

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `enable_caching` | false | Cache query results in Redis |
| `enable_batch` | true | Enable batch entity queries |
| `cache_ttl_seconds` | 600 | Cache time-to-live |
| `max_batch_size` | 50 | Maximum entities per batch |

## Replacing the GKG Binary

To switch to a different graph database (e.g., Neo4j):

1. Create `adapters/neo4j_adapter.py` implementing `GraphAnalyzerProtocol`
2. Update `factory.py`:

```python
if os.getenv("GRAPH_STORE") == "neo4j":
    self._analyzer = Neo4jAdapter(config.neo4j_url)
else:
    self._analyzer = GKGBinaryAdapter(config.gkg_binary)
```

3. Set environment variable: `GRAPH_STORE=neo4j`
4. Existing tests pass without modification

## Testing Strategy

Tests focus on **behavior**, not implementation:

- ✅ "Call graph returns both callers and callees"
- ✅ "Batch query returns results for all entities"
- ✅ "Cached queries don't re-execute analysis"
- ❌ "GKG binary called with correct Cypher syntax"

This allows replacing the GKG binary without breaking tests.

## Integration Points

### With LlamaIndex Service
GKG enriches vector search results with graph context:
```
LlamaIndex → GET /graph/related → GKG
         ← RelatedEntitiesResult ←
```

### With Indexer Worker
Indexer triggers repository indexing:
```
Indexer → POST /index → GKG
       ← {"status": "indexed"} ←
```
