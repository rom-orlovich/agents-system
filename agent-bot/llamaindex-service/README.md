# LlamaIndex Service

Hybrid RAG orchestration service combining vector search (ChromaDB) with graph traversal (GKG).

## Architecture

```
llamaindex-service/
├── core/                    # Business logic (framework-agnostic)
│   ├── interfaces.py        # Protocol definitions (ports)
│   ├── query_engine.py      # Hybrid query orchestration
│   └── models.py            # Domain models
├── adapters/                # External integrations (replaceable)
│   ├── chroma_adapter.py    # ChromaDB implementation
│   ├── gkg_adapter.py       # GKG service client
│   └── embedding_adapter.py # Embedding model wrapper
├── api/                     # FastAPI routes
│   └── routes.py
├── tests/                   # Behavior-based tests
│   ├── test_query_engine.py
│   └── conftest.py
├── docs/                    # Documentation
│   └── API.md
├── config.py                # Configuration with feature flags
├── main.py                  # Application entry point
└── README.md
```

## Quick Start

```bash
# Development
pip install -r requirements.txt
python main.py

# Docker
docker build -t llamaindex-service .
docker run -p 8002:8002 llamaindex-service
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROMADB_URL` | `http://chromadb:8000` | ChromaDB endpoint |
| `GKG_URL` | `http://gkg-service:8003` | GKG service endpoint |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `ENABLE_GKG_ENRICHMENT` | `true` | Enable graph enrichment |
| `ENABLE_RERANKING` | `true` | Enable cross-encoder reranking |
| `CACHE_TTL_SECONDS` | `300` | Query cache TTL |

## Feature Flags

Features can be enabled/disabled via environment variables:

```bash
ENABLE_GKG_ENRICHMENT=false  # Disable graph enrichment
ENABLE_RERANKING=false       # Disable reranking
ENABLE_CACHING=false         # Disable query caching
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/query` | POST | Hybrid query across all sources |
| `/query/code` | POST | Code-specific search |
| `/query/tickets` | POST | Jira ticket search |
| `/query/docs` | POST | Confluence search |
| `/graph/related` | POST | Find related entities via graph |
| `/collections` | GET | List ChromaDB collections |

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=core --cov-report=html

# Run specific test
pytest tests/test_query_engine.py -v
```

## Replacing Components

Components are defined via protocols (interfaces) in `core/interfaces.py`. To replace a component:

1. Implement the protocol (e.g., `VectorStoreProtocol`)
2. Update the adapter in `adapters/`
3. Update dependency injection in `main.py`

Example: Replacing ChromaDB with Pinecone:

```python
# adapters/pinecone_adapter.py
from core.interfaces import VectorStoreProtocol

class PineconeAdapter(VectorStoreProtocol):
    async def query(self, query: str, top_k: int, filters: dict) -> list[SearchResult]:
        # Pinecone-specific implementation
        pass
```
