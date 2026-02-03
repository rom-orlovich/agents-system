# LlamaIndex Service - Development Guide

## Service Overview

Hybrid RAG orchestration service that combines:
- **Vector Search**: Semantic similarity via ChromaDB
- **Graph Traversal**: Code relationships via GKG
- **Query Routing**: Intent-based routing to appropriate indexes

## Architecture Principles

### 1. Dependency Injection via Protocols

All external dependencies are defined as protocols in `core/interfaces.py`:

```python
class VectorStoreProtocol(Protocol):
    async def query(self, query: str, top_k: int, filters: dict) -> list[SearchResult]: ...

class GraphStoreProtocol(Protocol):
    async def get_related(self, entity: str, relationship: str) -> list[Entity]: ...
```

### 2. Core vs Adapters Separation

- `core/`: Business logic, pure Python, no external dependencies
- `adapters/`: External service integrations (ChromaDB, GKG, etc.)

### 3. Feature Flags

All features are toggleable via `FeatureFlags` in config:

```python
class FeatureFlags(BaseModel):
    enable_gkg_enrichment: bool = True
    enable_reranking: bool = True
    enable_caching: bool = True
```

## Key Commands

```bash
# Run service
python main.py

# Run tests
pytest tests/ -v

# Type check
mypy .

# Format
ruff format .
```

## Testing Guidelines

1. **Test behavior, not implementation**
2. **Use fakes/mocks for external services**
3. **Test at the boundary (API level) when possible**

Example test structure:

```python
# tests/test_query_engine.py
async def test_hybrid_query_returns_relevant_results(
    query_engine: HybridQueryEngine,
    fake_vector_store: FakeVectorStore,
):
    # Given
    fake_vector_store.add_document("auth code", {"type": "code"})

    # When
    results = await query_engine.query("authentication", org_id="test")

    # Then
    assert len(results) > 0
    assert "auth" in results[0].content
```

## Adding New Features

1. Define interface in `core/interfaces.py`
2. Implement adapter in `adapters/`
3. Add feature flag in `config.py`
4. Wire up in `main.py`
5. Add tests in `tests/`

## Error Handling

- Use domain exceptions from `core/exceptions.py`
- Adapters translate external errors to domain exceptions
- API layer handles exceptions and returns appropriate HTTP codes

## Performance Considerations

- Query caching enabled by default (5 min TTL)
- Embedding model loaded once at startup
- Async all the way (httpx, asyncio)
