# Indexer Worker

Background worker service for indexing data sources (GitHub, Jira, Confluence) into vector and graph stores for knowledge retrieval.

## Quick Start

```bash
# Run with Docker (recommended)
docker-compose --profile knowledge up indexer-worker

# Run locally
cd indexer-worker
pip install -r requirements.txt
python worker.py
```

## Architecture

The service follows a modular, protocol-based architecture:

```
indexer-worker/
├── core/                    # Business logic (framework-agnostic)
│   ├── interfaces.py        # Protocol definitions
│   ├── models.py            # Domain models
│   └── orchestrator.py      # Job orchestration logic
│
├── adapters/                # External implementations
│   ├── source_adapters/     # Data source fetchers
│   │   ├── github.py        # GitHub repository indexer
│   │   ├── jira.py          # Jira ticket indexer
│   │   └── confluence.py    # Confluence page indexer
│   ├── storage_adapters/    # Storage backends
│   │   ├── chromadb.py      # ChromaDB vector store
│   │   └── gkg.py           # GKG graph store
│   └── queue_adapter.py     # Redis job queue
│
├── tests/                   # Behavior-driven tests
├── docs/                    # Documentation
├── factory.py               # Dependency injection
└── worker.py                # Application entry point
```

## How It Works

1. Worker polls Redis queue for indexing jobs
2. Fetches source configuration from Dashboard API
3. For each enabled source:
   - GitHub: Clone/pull repos, chunk code, generate embeddings, index to GKG
   - Jira: Fetch tickets via API, chunk content, generate embeddings
   - Confluence: Fetch pages via API, chunk content, generate embeddings
4. Store embeddings in ChromaDB, code graph in GKG
5. Update job status and publish completion event

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `CHROMADB_URL` | `http://chromadb:8000` | ChromaDB endpoint |
| `GKG_URL` | `http://gkg-service:8003` | GKG service endpoint |
| `REPOS_DIR` | `/data/repos` | Repository storage path |
| `GITHUB_TOKEN` | - | GitHub API token |
| `JIRA_URL` | - | Jira instance URL |
| `JIRA_EMAIL` | - | Jira authentication email |
| `JIRA_API_TOKEN` | - | Jira API token |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `CHUNK_SIZE` | `1500` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |

## Replacing Components

### Use Different Embedding Model

```python
# In factory.py
from adapters.embedding_adapters import OpenAIEmbedding

container.set_embedding_provider(OpenAIEmbedding(api_key="..."))
```

### Use Different Vector Store

```python
# In factory.py
from adapters.storage_adapters import PineconeStore

container.set_vector_store(PineconeStore(api_key="..."))
```

## Testing

```bash
# Run behavior tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=core --cov-report=term-missing
```

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `ENABLE_GKG_INDEXING` | `true` | Index code to graph store |
| `ENABLE_PARALLEL` | `true` | Process repos in parallel |
| `MAX_PARALLEL_REPOS` | `5` | Max concurrent repo indexing |
