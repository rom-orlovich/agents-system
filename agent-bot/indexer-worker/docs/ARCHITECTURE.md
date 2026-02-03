# Indexer Worker Architecture

## Overview

The Indexer Worker is a background service that processes indexing jobs from a Redis queue. It fetches data from various sources (GitHub, Jira, Confluence), chunks the content, generates embeddings, and stores them in vector (ChromaDB) and graph (GKG) stores.

## Design Principles

1. **Protocol-Based Interfaces** - All external dependencies implement typed protocols
2. **Dependency Injection** - Components wired via factory at startup
3. **Pluggable Sources** - New data sources easily added via protocol implementation
4. **Behavior-Focused Testing** - Tests verify job orchestration, not API details

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Worker Loop                              │
│                         (worker.py)                              │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Indexer Orchestrator                          │
│                  (core/orchestrator.py)                          │
│                                                                  │
│  • Job processing lifecycle                                      │
│  • Source iteration                                              │
│  • Chunk storage orchestration                                   │
│  • Status updates                                                │
└────────┬────────────────┬────────────────┬─────────────────────┘
         │                │                │
         ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Source       │  │ Vector       │  │ Graph        │
│ Indexers     │  │ Store        │  │ Store        │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Directory Structure

```
indexer-worker/
├── core/                    # Business logic
│   ├── interfaces.py        # Protocol definitions
│   ├── models.py            # Domain models
│   └── orchestrator.py      # Job orchestration
│
├── adapters/
│   ├── source_adapters/     # Data source implementations
│   │   ├── github.py
│   │   ├── jira.py
│   │   └── confluence.py
│   ├── storage_adapters/    # Storage implementations
│   │   ├── chromadb.py
│   │   └── gkg.py
│   └── queue_adapter.py     # Redis queue
│
├── indexers/                # Legacy indexer implementations
│   ├── github_indexer.py    # (to be migrated to adapters)
│   ├── jira_indexer.py
│   └── confluence_indexer.py
│
├── tests/
│   ├── conftest.py
│   └── test_orchestrator_behavior.py
│
├── docs/
├── factory.py
├── worker.py
├── README.md
└── CLAUDE.md
```

## Protocol Interfaces

### SourceIndexerProtocol
Data source indexing:
- `fetch_items()` - Fetch items from source
- `index_items()` - Convert items to chunks

### VectorStoreProtocol
Vector storage:
- `upsert_code_chunks()` - Store code with embeddings
- `upsert_document_chunks()` - Store docs with embeddings
- `health_check()` - Check connectivity

### GraphStoreProtocol
Graph storage:
- `index_repository()` - Index repo to graph
- `health_check()` - Check connectivity

### JobQueueProtocol
Job management:
- `pop_job()` - Get next job from queue
- `update_status()` - Update job status
- `publish_completion()` - Notify job done

## Data Flow

### Job Processing Flow

```
1. Worker polls Redis queue (blocking)
2. Job received → Orchestrator.process_job()
3. Status → "running", published to Redis
4. Fetch source configs from Dashboard API
5. For each enabled source:
   a. Create appropriate indexer (GitHub/Jira/Confluence)
   b. Fetch items from source
   c. Chunk content into embeddings-ready pieces
   d. Generate embeddings via model
   e. Store to ChromaDB
   f. (GitHub only) Index to GKG graph store
   g. Update progress %
6. Status → "completed" or "failed"
7. Publish completion event
```

### Source Type Mapping

| Source | Indexer | Collection | Extra Storage |
|--------|---------|------------|---------------|
| GitHub | GitHubIndexer | code | GKG (optional) |
| Jira | JiraIndexer | jira_tickets | - |
| Confluence | ConfluenceIndexer | confluence_docs | - |

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `enable_gkg_indexing` | true | Index code repos to GKG |
| `enable_parallel` | true | Process repos in parallel |
| `max_parallel_repos` | 5 | Max concurrent repo processing |
| `batch_size` | 100 | Chunks per embedding batch |

## Adding a New Data Source

1. Create adapter implementing `SourceIndexerProtocol`:
   ```python
   class SlackIndexer:
       async def fetch_items(self) -> list[dict]:
           # Fetch messages from Slack API

       async def index_items(self, items) -> list[DocumentChunk]:
           # Convert messages to chunks
   ```

2. Register in indexer factory:
   ```python
   def create_indexer(org_id, source_type, config):
       if source_type == "slack":
           return SlackIndexer(org_id, SlackConfig(**config))
   ```

3. Add tests in `tests/test_orchestrator_behavior.py`

## Error Handling

- Individual item failures don't fail the job
- Failed items are counted in `items_failed`
- Job only fails on critical errors (source fetch, storage down)
- All errors logged with structured logging
