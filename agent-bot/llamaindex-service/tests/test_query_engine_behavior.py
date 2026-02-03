import pytest

from core.query_engine import HybridQueryEngine, FeatureFlags
from tests.conftest import MockVectorStore, MockGraphStore, MockCache


class TestHybridQueryBehavior:
    """Test query engine business logic and behavior."""

    @pytest.mark.asyncio
    async def test_hybrid_query_returns_results_from_multiple_sources(
        self,
        mock_vector_store: MockVectorStore,
    ):
        """Querying multiple source types should return results from all sources."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            feature_flags=FeatureFlags(
                enable_gkg_enrichment=False, enable_caching=False
            ),
        )

        response = await engine.query(
            query="order processing",
            org_id="test-org",
            source_types=["code", "jira", "confluence"],
            top_k=10,
        )

        assert response.total_results > 0
        source_types_found = {r.source_type for r in response.results}
        assert len(source_types_found) >= 1
        assert response.query == "order processing"

    @pytest.mark.asyncio
    async def test_query_respects_top_k_limit(
        self,
        mock_vector_store: MockVectorStore,
    ):
        """Results should be limited to top_k items."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            feature_flags=FeatureFlags(
                enable_gkg_enrichment=False, enable_caching=False
            ),
        )

        response = await engine.query(
            query="order processing",
            org_id="test-org",
            top_k=1,
        )

        assert len(response.results) <= 1

    @pytest.mark.asyncio
    async def test_results_sorted_by_relevance(
        self,
        mock_vector_store: MockVectorStore,
    ):
        """Results should be sorted by relevance score in descending order."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            feature_flags=FeatureFlags(
                enable_gkg_enrichment=False, enable_caching=False
            ),
        )

        response = await engine.query(
            query="order processing",
            org_id="test-org",
            top_k=10,
        )

        if len(response.results) > 1:
            scores = [r.relevance_score for r in response.results]
            assert scores == sorted(scores, reverse=True)


class TestCodeQueryBehavior:
    """Test code-specific query behavior."""

    @pytest.mark.asyncio
    async def test_code_query_only_searches_code_collection(
        self,
        mock_vector_store: MockVectorStore,
    ):
        """Code query should only search the code collection."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            feature_flags=FeatureFlags(
                enable_gkg_enrichment=False, enable_caching=False
            ),
        )

        response = await engine.query_code(
            query="process order",
            org_id="test-org",
        )

        assert all(r.source_type == "code" for r in response.results)
        assert response.source_types_queried == ["code"]

    @pytest.mark.asyncio
    async def test_code_query_applies_repository_filter(
        self,
        mock_vector_store: MockVectorStore,
    ):
        """Code query should pass repository filter to vector store."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            feature_flags=FeatureFlags(
                enable_gkg_enrichment=False, enable_caching=False
            ),
        )

        await engine.query_code(
            query="process order",
            org_id="test-org",
            repo_filter="api-service",
        )

        assert len(mock_vector_store.query_calls) == 1
        assert mock_vector_store.query_calls[0]["filters"]["repo"] == "api-service"


class TestGraphEnrichmentBehavior:
    """Test graph enrichment behavior."""

    @pytest.mark.asyncio
    async def test_graph_enrichment_adds_context_to_code_results(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
    ):
        """Graph enrichment should add relationship context to code results."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            feature_flags=FeatureFlags(
                enable_gkg_enrichment=True, enable_caching=False
            ),
        )

        response = await engine.query(
            query="process order",
            org_id="test-org",
            source_types=["code"],
            top_k=10,
        )

        code_results = [r for r in response.results if r.source_type == "code"]
        assert len(code_results) > 0

    @pytest.mark.asyncio
    async def test_graph_enrichment_disabled_skips_graph_lookup(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
    ):
        """Disabled graph enrichment should not query graph store."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            feature_flags=FeatureFlags(
                enable_gkg_enrichment=False, enable_caching=False
            ),
        )

        await engine.query(
            query="process order",
            org_id="test-org",
            source_types=["code"],
        )

        assert len(mock_graph_store._calls) == 0


class TestCachingBehavior:
    """Test caching behavior."""

    @pytest.mark.asyncio
    async def test_cached_results_returned_on_repeat_query(
        self,
        mock_vector_store: MockVectorStore,
        mock_cache: MockCache,
    ):
        """Repeat queries should return cached results."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            cache=mock_cache,
            feature_flags=FeatureFlags(
                enable_caching=True, enable_gkg_enrichment=False
            ),
        )

        first_response = await engine.query(
            query="order processing",
            org_id="test-org",
            source_types=["code"],
            top_k=5,
        )
        assert not first_response.cached

        call_count_after_first = len(mock_vector_store.query_calls)

        second_response = await engine.query(
            query="order processing",
            org_id="test-org",
            source_types=["code"],
            top_k=5,
        )
        assert second_response.cached

        assert len(mock_vector_store.query_calls) == call_count_after_first

    @pytest.mark.asyncio
    async def test_caching_disabled_always_queries_store(
        self,
        mock_vector_store: MockVectorStore,
        mock_cache: MockCache,
    ):
        """Disabled caching should always query the vector store."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            cache=mock_cache,
            feature_flags=FeatureFlags(
                enable_caching=False, enable_gkg_enrichment=False
            ),
        )

        await engine.query(query="test", org_id="org", source_types=["code"], top_k=5)
        first_count = len(mock_vector_store.query_calls)

        await engine.query(query="test", org_id="org", source_types=["code"], top_k=5)

        assert len(mock_vector_store.query_calls) > first_count


class TestGraphRelatedEntitiesBehavior:
    """Test graph relationship query behavior."""

    @pytest.mark.asyncio
    async def test_get_related_entities_returns_relationships(
        self,
        mock_vector_store: MockVectorStore,
        mock_graph_store: MockGraphStore,
    ):
        """Getting related entities should return relationship map."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
        )

        relationships = await engine.get_related_entities(
            entity="process_order",
            entity_type="function",
            org_id="test-org",
            relationship="all",
        )

        assert isinstance(relationships, dict)
        assert "calls" in relationships or "called_by" in relationships

    @pytest.mark.asyncio
    async def test_get_related_entities_without_graph_store_returns_empty(
        self,
        mock_vector_store: MockVectorStore,
    ):
        """No graph store should return empty relationships."""
        engine = HybridQueryEngine(
            vector_store=mock_vector_store,
            graph_store=None,
        )

        relationships = await engine.get_related_entities(
            entity="process_order",
            entity_type="function",
            org_id="test-org",
        )

        assert relationships == {}
