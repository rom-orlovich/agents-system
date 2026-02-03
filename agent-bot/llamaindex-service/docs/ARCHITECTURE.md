# LlamaIndex Service Architecture

## Overview

The LlamaIndex service is a modular hybrid RAG (Retrieval-Augmented Generation) orchestration service that combines vector search with graph-based knowledge for enhanced code understanding.

## Design Principles

1. **Protocol-Based Interfaces** - All external dependencies implement typed protocols
2. **Dependency Injection** - Components are injected at runtime via factory
3. **Feature Flags** - Capabilities can be toggled without code changes
4. **Behavior-Focused Testing** - Tests verify business behavior, not implementation

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
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ VectorStore │  │ GraphStore  │  │    Cache    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Business Logic                         │
│                   (core/query_engine.py)                         │
│                                                                  │
│  • Hybrid query orchestration                                    │
│  • Result aggregation and ranking                                │
│  • Graph enrichment logic                                        │
│  • Cache management                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
llamaindex-service/
├── core/                    # Business logic (framework-agnostic)
│   ├── interfaces.py        # Protocol definitions
│   ├── models.py            # Domain models
│   └── query_engine.py      # Core orchestration logic
│
├── adapters/                # External service implementations
│   ├── chroma_adapter.py    # ChromaDB vector store
│   ├── gkg_adapter.py       # GitLab Knowledge Graph
│   └── redis_cache_adapter.py  # Redis/in-memory cache
│
├── api/                     # HTTP layer
│   └── routes.py            # FastAPI route handlers
│
├── tests/                   # Behavior-driven tests
│   ├── conftest.py          # Test fixtures and mocks
│   └── test_query_engine_behavior.py
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

### VectorStoreProtocol
Defines vector similarity search operations:
- `query()` - Search by semantic similarity
- `list_collections()` - List available collections
- `health_check()` - Verify connectivity

### GraphStoreProtocol
Defines graph traversal operations:
- `get_related_entities()` - Find related code entities
- `get_dependencies()` - Trace file dependencies
- `health_check()` - Verify connectivity

### CacheProtocol
Defines caching operations:
- `get()` - Retrieve cached value
- `set()` - Store value with TTL
- `delete()` - Remove cached value

## Data Flow

### Hybrid Query Flow

```
1. Request → API Router → Query Engine
2. Query Engine checks cache (if enabled)
3. If miss: Execute vector search across collections
4. If code results + GKG enabled: Enrich with graph context
5. If reranking enabled: Apply cross-encoder reranking
6. Cache result and return
```

### Source Type Mapping

| Source Type | Collection Name | Content |
|-------------|-----------------|---------|
| code | code | Source code chunks |
| jira | jira_tickets | Jira issues |
| confluence | confluence_docs | Confluence pages |
| github_issues | github_issues | GitHub issues |

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `enable_gkg_enrichment` | true | Add graph context to code results |
| `enable_caching` | true | Cache query results |
| `enable_reranking` | false | Apply cross-encoder reranking |
| `cache_ttl_seconds` | 300 | Cache time-to-live |

## Replacing Components

### Example: Switch to Pinecone

1. Create `adapters/pinecone_adapter.py` implementing `VectorStoreProtocol`
2. Update `factory.py` to use Pinecone adapter
3. Set environment variable `VECTOR_STORE=pinecone`

```python
# factory.py
if os.getenv("VECTOR_STORE") == "pinecone":
    self._vector_store = PineconeVectorStore(config.pinecone_url)
else:
    self._vector_store = ChromaVectorStore(config.chromadb_url)
```

### Example: Disable GKG

```bash
ENABLE_GKG=false docker-compose up llamaindex-service
```

## Testing Strategy

Tests focus on **behavior**, not implementation:

- ✅ "Query returns results from multiple sources"
- ✅ "Results are sorted by relevance score"
- ✅ "Cached queries don't hit vector store"
- ❌ "ChromaDB client called with specific parameters"

This allows refactoring internals without breaking tests.
