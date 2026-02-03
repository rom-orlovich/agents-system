import pytest

from core.orchestrator import IndexerOrchestrator, FeatureFlags
from core.models import CodeChunk, DocumentChunk
from tests.conftest import (
    MockVectorStore,
    MockGraphStore,
    MockEmbeddingProvider,
    MockJobQueue,
    MockSourceFetcher,
    MockSourceIndexer,
)


def create_mock_indexer_factory(
    chunks: list[CodeChunk] | list[DocumentChunk] | None = None,
):
    """Create a factory that returns mock indexers."""

    def factory(org_id: str, source_type: str, config: dict):
        return MockSourceIndexer(
            items=[{"id": "item-1"}],
            chunks=chunks or [],
        )

    return factory


class TestJobProcessingBehavior:
    """Test job processing behavior."""

    @pytest.mark.asyncio
    async def test_job_updates_status_to_running(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
        mock_embedding: MockEmbeddingProvider,
        mock_queue: MockJobQueue,
        mock_source_fetcher: MockSourceFetcher,
    ):
        """Job processing should update status multiple times."""
        orchestrator = IndexerOrchestrator(
            job_queue=mock_queue,
            source_fetcher=mock_source_fetcher,
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding,
            indexer_factory=create_mock_indexer_factory(),
        )

        job = {"job_id": "job-1", "org_id": "test-org"}
        await orchestrator.process_job(job)

        assert len(mock_queue.statuses) >= 2

    @pytest.mark.asyncio
    async def test_successful_job_completes(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
        mock_embedding: MockEmbeddingProvider,
        mock_queue: MockJobQueue,
        mock_source_fetcher: MockSourceFetcher,
    ):
        """Successful job should complete."""
        orchestrator = IndexerOrchestrator(
            job_queue=mock_queue,
            source_fetcher=mock_source_fetcher,
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding,
            indexer_factory=create_mock_indexer_factory(),
        )

        job = {"job_id": "job-1", "org_id": "test-org"}
        status = await orchestrator.process_job(job)

        assert status.status == "completed"
        assert status.completed_at is not None

    @pytest.mark.asyncio
    async def test_job_completion_published(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
        mock_embedding: MockEmbeddingProvider,
        mock_queue: MockJobQueue,
        mock_source_fetcher: MockSourceFetcher,
    ):
        """Job completion should be published."""
        orchestrator = IndexerOrchestrator(
            job_queue=mock_queue,
            source_fetcher=mock_source_fetcher,
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding,
            indexer_factory=create_mock_indexer_factory(),
        )

        job = {"job_id": "job-1", "org_id": "test-org"}
        await orchestrator.process_job(job)

        assert len(mock_queue.completions) == 1
        assert mock_queue.completions[0].job_id == "job-1"


class TestChunkStorageBehavior:
    """Test chunk storage behavior."""

    @pytest.mark.asyncio
    async def test_code_chunks_stored_to_vector_store(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
        mock_embedding: MockEmbeddingProvider,
        mock_queue: MockJobQueue,
        sample_code_chunks: list[CodeChunk],
    ):
        """Code chunks should be stored to vector store."""
        source_config = [
            {
                "source_id": "src-1",
                "org_id": "test-org",
                "source_type": "github",
                "name": "API",
                "enabled": True,
                "config_json": "{}",
            }
        ]
        mock_fetcher = MockSourceFetcher(sources=source_config)

        orchestrator = IndexerOrchestrator(
            job_queue=mock_queue,
            source_fetcher=mock_fetcher,
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding,
            indexer_factory=create_mock_indexer_factory(chunks=sample_code_chunks),
        )

        job = {"job_id": "job-1", "org_id": "test-org"}
        await orchestrator.process_job(job)

        upsert_calls = [
            c for c in mock_vector_store.calls if c["method"] == "upsert_code_chunks"
        ]
        assert len(upsert_calls) > 0

    @pytest.mark.asyncio
    async def test_document_chunks_stored_with_correct_collection(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
        mock_embedding: MockEmbeddingProvider,
        mock_queue: MockJobQueue,
        sample_document_chunks: list[DocumentChunk],
    ):
        """Jira chunks should be stored to jira_tickets collection."""
        source_config = [
            {
                "source_id": "src-1",
                "org_id": "test-org",
                "source_type": "jira",
                "name": "Jira",
                "enabled": True,
                "config_json": "{}",
            }
        ]
        mock_fetcher = MockSourceFetcher(sources=source_config)

        orchestrator = IndexerOrchestrator(
            job_queue=mock_queue,
            source_fetcher=mock_fetcher,
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding,
            indexer_factory=create_mock_indexer_factory(chunks=sample_document_chunks),
        )

        job = {"job_id": "job-1", "org_id": "test-org"}
        await orchestrator.process_job(job)

        upsert_calls = [
            c
            for c in mock_vector_store.calls
            if c["method"] == "upsert_document_chunks"
        ]
        assert len(upsert_calls) > 0
        assert upsert_calls[0]["collection"] == "jira_tickets"


class TestDisabledSourceBehavior:
    """Test disabled source behavior."""

    @pytest.mark.asyncio
    async def test_disabled_source_skipped(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
        mock_embedding: MockEmbeddingProvider,
        mock_queue: MockJobQueue,
    ):
        """Disabled sources should be skipped."""
        source_config = [
            {
                "source_id": "src-1",
                "org_id": "test-org",
                "source_type": "github",
                "name": "API",
                "enabled": False,
                "config_json": "{}",
            }
        ]
        mock_fetcher = MockSourceFetcher(sources=source_config)

        orchestrator = IndexerOrchestrator(
            job_queue=mock_queue,
            source_fetcher=mock_fetcher,
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding,
            indexer_factory=create_mock_indexer_factory(),
        )

        job = {"job_id": "job-1", "org_id": "test-org"}
        await orchestrator.process_job(job)

        assert len(mock_vector_store.calls) == 0


class TestGraphIndexingBehavior:
    """Test graph indexing behavior."""

    @pytest.mark.asyncio
    async def test_graph_indexing_when_enabled(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
        mock_embedding: MockEmbeddingProvider,
        mock_queue: MockJobQueue,
    ):
        """Graph indexing should occur when enabled."""
        orchestrator = IndexerOrchestrator(
            job_queue=mock_queue,
            source_fetcher=MockSourceFetcher([]),
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding,
            indexer_factory=create_mock_indexer_factory(),
            feature_flags=FeatureFlags(enable_gkg_indexing=True),
        )

        result = await orchestrator.index_to_graph("test-org", "/path/to/repo")

        assert result is True
        assert len(mock_graph_store._calls) == 1

    @pytest.mark.asyncio
    async def test_graph_indexing_skipped_when_disabled(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
        mock_embedding: MockEmbeddingProvider,
        mock_queue: MockJobQueue,
    ):
        """Graph indexing should be skipped when disabled."""
        orchestrator = IndexerOrchestrator(
            job_queue=mock_queue,
            source_fetcher=MockSourceFetcher([]),
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding,
            indexer_factory=create_mock_indexer_factory(),
            feature_flags=FeatureFlags(enable_gkg_indexing=False),
        )

        result = await orchestrator.index_to_graph("test-org", "/path/to/repo")

        assert result is False
        assert len(mock_graph_store._calls) == 0


class TestHealthCheckBehavior:
    """Test health check behavior."""

    @pytest.mark.asyncio
    async def test_health_check_returns_all_components(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
        mock_embedding: MockEmbeddingProvider,
        mock_queue: MockJobQueue,
    ):
        """Health check should return status of all components."""
        orchestrator = IndexerOrchestrator(
            job_queue=mock_queue,
            source_fetcher=MockSourceFetcher([]),
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding,
            indexer_factory=create_mock_indexer_factory(),
        )

        health = await orchestrator.is_healthy()

        assert "queue" in health
        assert "vector_store" in health
        assert "graph_store" in health
