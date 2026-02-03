from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from core.interfaces import (
    SourceIndexerProtocol,
    VectorStoreProtocol,
    GraphStoreProtocol,
    EmbeddingProtocol,
    JobQueueProtocol,
    SourceConfigFetcherProtocol,
)
from core.models import JobStatus, SourceConfig, CodeChunk, DocumentChunk


@dataclass
class FeatureFlags:
    """Feature flags for indexer."""

    enable_gkg_indexing: bool = True
    enable_parallel: bool = True
    max_parallel_repos: int = 5
    batch_size: int = 100


IndexerFactory = Callable[[str, str, dict], SourceIndexerProtocol]


class IndexerOrchestrator:
    """
    Orchestrates indexing jobs across multiple sources.

    All external dependencies are injected via protocols.
    """

    def __init__(
        self,
        job_queue: JobQueueProtocol,
        source_fetcher: SourceConfigFetcherProtocol,
        vector_store: VectorStoreProtocol,
        graph_store: GraphStoreProtocol | None,
        embedding_provider: EmbeddingProtocol,
        indexer_factory: IndexerFactory,
        feature_flags: FeatureFlags | None = None,
    ):
        self._queue = job_queue
        self._source_fetcher = source_fetcher
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._embedding = embedding_provider
        self._indexer_factory = indexer_factory
        self._flags = feature_flags or FeatureFlags()

    async def process_job(self, job: dict) -> JobStatus:
        """Process a single indexing job."""
        job_id = job.get("job_id", str(uuid.uuid4()))
        org_id = job.get("org_id")
        source_id = job.get("source_id")
        job_type = job.get("job_type", "incremental")

        status = JobStatus(
            job_id=job_id,
            org_id=org_id,
            source_id=source_id,
            job_type=job_type,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        await self._queue.update_status(status)

        try:
            source_data = await self._source_fetcher.fetch_sources(org_id, source_id)
            sources = [self._parse_source(s) for s in source_data]

            for source in sources:
                await self._index_source(source, status)

            status.status = "completed"
            status.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            status.status = "failed"
            status.error_message = str(e)
            status.completed_at = datetime.now(timezone.utc)

        await self._queue.update_status(status)
        await self._queue.publish_completion(status)

        return status

    def _parse_source(self, data: dict) -> SourceConfig:
        import json

        config_data = data.get("config_json", "{}")
        if isinstance(config_data, str):
            config_data = json.loads(config_data)

        return SourceConfig(
            source_id=data.get("source_id"),
            org_id=data.get("org_id"),
            source_type=data.get("source_type"),
            name=data.get("name"),
            enabled=data.get("enabled", True),
            config=config_data,
        )

    async def _index_source(self, source: SourceConfig, status: JobStatus) -> None:
        """Index a single data source."""
        if not source.enabled:
            return

        indexer = self._indexer_factory(
            source.org_id,
            source.source_type,
            source.config,
        )

        items = await indexer.fetch_items()
        status.items_total += len(items)
        await self._queue.update_status(status)

        chunks = await indexer.index_items(items)

        await self._store_chunks(source, chunks, status)

    async def _store_chunks(
        self,
        source: SourceConfig,
        chunks: list[CodeChunk] | list[DocumentChunk],
        status: JobStatus,
    ) -> None:
        """Store chunks to vector store with embeddings."""
        if not chunks:
            return

        for i in range(0, len(chunks), self._flags.batch_size):
            batch = chunks[i : i + self._flags.batch_size]
            documents = [c.content for c in batch]
            embeddings = self._embedding.encode(documents)

            if source.source_type == "github":
                await self._vector_store.upsert_code_chunks(
                    org_id=source.org_id,
                    chunks=batch,
                    embeddings=embeddings,
                )
            else:
                collection = (
                    "jira_tickets"
                    if source.source_type == "jira"
                    else "confluence_docs"
                )
                await self._vector_store.upsert_document_chunks(
                    org_id=source.org_id,
                    chunks=batch,
                    embeddings=embeddings,
                    collection=collection,
                )

            status.items_processed += len(batch)
            status.progress_percent = int(
                (status.items_processed / max(status.items_total, 1)) * 100
            )
            await self._queue.update_status(status)

    async def index_to_graph(self, org_id: str, repo_path: str) -> bool:
        """Index repository to graph store."""
        if not self._flags.enable_gkg_indexing or not self._graph_store:
            return False

        return await self._graph_store.index_repository(org_id, repo_path)

    async def is_healthy(self) -> dict[str, bool]:
        """Check health of all dependencies."""
        return {
            "queue": await self._queue.health_check(),
            "vector_store": await self._vector_store.health_check(),
            "graph_store": (
                await self._graph_store.health_check() if self._graph_store else True
            ),
        }
