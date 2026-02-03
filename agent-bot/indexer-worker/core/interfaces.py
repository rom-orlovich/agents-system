from typing import Protocol, runtime_checkable
from core.models import CodeChunk, DocumentChunk, JobStatus


@runtime_checkable
class SourceIndexerProtocol(Protocol):
    """Protocol for data source indexers."""

    async def fetch_items(self) -> list[dict]:
        """Fetch items from source."""
        ...

    async def index_items(
        self, items: list[dict]
    ) -> list[CodeChunk] | list[DocumentChunk]:
        """Index items into chunks."""
        ...


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Protocol for vector store implementations."""

    async def upsert_code_chunks(
        self,
        org_id: str,
        chunks: list[CodeChunk],
        embeddings: list[list[float]],
    ) -> None:
        """Store code chunks with embeddings."""
        ...

    async def upsert_document_chunks(
        self,
        org_id: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        collection: str,
    ) -> None:
        """Store document chunks with embeddings."""
        ...

    async def health_check(self) -> bool:
        """Check if store is healthy."""
        ...


@runtime_checkable
class GraphStoreProtocol(Protocol):
    """Protocol for graph store implementations."""

    async def index_repository(self, org_id: str, repo_path: str) -> bool:
        """Index repository to graph store."""
        ...

    async def health_check(self) -> bool:
        """Check if store is healthy."""
        ...


@runtime_checkable
class EmbeddingProtocol(Protocol):
    """Protocol for embedding model implementations."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...


@runtime_checkable
class JobQueueProtocol(Protocol):
    """Protocol for job queue implementations."""

    async def pop_job(self, timeout: int) -> dict | None:
        """Pop next job from queue."""
        ...

    async def update_status(self, status: JobStatus) -> None:
        """Update job status."""
        ...

    async def publish_completion(self, status: JobStatus) -> None:
        """Publish job completion event."""
        ...

    async def health_check(self) -> bool:
        """Check if queue is healthy."""
        ...


@runtime_checkable
class SourceConfigFetcherProtocol(Protocol):
    """Protocol for fetching source configurations."""

    async def fetch_sources(
        self,
        org_id: str,
        source_id: str | None,
    ) -> list[dict]:
        """Fetch source configurations."""
        ...
