from typing import Protocol, runtime_checkable
from core.models import SearchResult, GraphEntity


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Protocol for vector store implementations (ChromaDB, Pinecone, etc.)."""

    async def query(
        self,
        query_text: str,
        collection: str,
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[SearchResult]:
        """Query vectors by semantic similarity."""
        ...

    async def list_collections(self) -> list[str]:
        """List available collections."""
        ...

    async def health_check(self) -> bool:
        """Check if store is healthy."""
        ...


@runtime_checkable
class GraphStoreProtocol(Protocol):
    """Protocol for graph store implementations (GKG, Neo4j, etc.)."""

    async def get_related_entities(
        self,
        entity: str,
        entity_type: str,
        relationship: str,
        org_id: str,
    ) -> dict[str, list[GraphEntity]]:
        """Find entities related to the given entity."""
        ...

    async def get_dependencies(
        self,
        file_path: str,
        org_id: str,
        depth: int,
    ) -> list[GraphEntity]:
        """Get file dependencies."""
        ...

    async def health_check(self) -> bool:
        """Check if store is healthy."""
        ...


@runtime_checkable
class EmbeddingProtocol(Protocol):
    """Protocol for embedding model implementations."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        ...


@runtime_checkable
class CacheProtocol(Protocol):
    """Protocol for cache implementations (Redis, in-memory, etc.)."""

    async def get(self, key: str) -> str | None:
        """Get cached value."""
        ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Set cached value with TTL."""
        ...

    async def delete(self, key: str) -> None:
        """Delete cached value."""
        ...


@runtime_checkable
class RerankerProtocol(Protocol):
    """Protocol for reranking implementations."""

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Rerank documents and return (index, score) pairs."""
        ...
