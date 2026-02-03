import pytest

from core.graph_analyzer import GraphAnalyzerService, FeatureFlags
from tests.conftest import MockGraphAnalyzer, MockCache


class TestDependencyAnalysisBehavior:
    """Test dependency analysis behavior."""

    @pytest.mark.asyncio
    async def test_dependency_query_returns_file_dependencies(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Dependency query should return related files."""
        service = GraphAnalyzerService(analyzer=mock_analyzer)

        result = await service.query_dependencies(
            org_id="test-org",
            repo="api-service",
            file_path="src/orders.py",
            depth=3,
        )

        assert result.file_path == "src/orders.py"
        assert result.repo == "api-service"
        assert len(result.dependencies) > 0

    @pytest.mark.asyncio
    async def test_dependency_query_respects_depth_parameter(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Depth parameter should be passed to analyzer."""
        service = GraphAnalyzerService(analyzer=mock_analyzer)

        await service.query_dependencies(
            org_id="test-org",
            repo="api-service",
            file_path="src/orders.py",
            depth=5,
        )

        assert len(mock_analyzer.calls) == 1
        assert mock_analyzer.calls[0]["depth"] == 5


class TestCallGraphBehavior:
    """Test call graph analysis behavior."""

    @pytest.mark.asyncio
    async def test_call_graph_returns_callers_and_callees(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Call graph query should return both callers and callees."""
        service = GraphAnalyzerService(analyzer=mock_analyzer)

        result = await service.get_call_graph(
            org_id="test-org",
            repo="api-service",
            function_name="process_order",
            direction="both",
            depth=2,
        )

        assert result.function_name == "process_order"
        assert len(result.callers) > 0
        assert len(result.callees) > 0

    @pytest.mark.asyncio
    async def test_call_graph_respects_direction_callers_only(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Callers-only direction should return only callers."""
        service = GraphAnalyzerService(analyzer=mock_analyzer)

        result = await service.get_call_graph(
            org_id="test-org",
            repo="api-service",
            function_name="process_order",
            direction="callers",
            depth=2,
        )

        assert len(result.callers) > 0
        assert len(result.callees) == 0

    @pytest.mark.asyncio
    async def test_call_graph_respects_direction_callees_only(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Callees-only direction should return only callees."""
        service = GraphAnalyzerService(analyzer=mock_analyzer)

        result = await service.get_call_graph(
            org_id="test-org",
            repo="api-service",
            function_name="process_order",
            direction="callees",
            depth=2,
        )

        assert len(result.callers) == 0
        assert len(result.callees) > 0


class TestClassHierarchyBehavior:
    """Test class hierarchy analysis behavior."""

    @pytest.mark.asyncio
    async def test_hierarchy_returns_parents_and_children(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Hierarchy query should return parent and child classes."""
        mock_analyzer._parents = [
            pytest.importorskip("core.models").HierarchyNode(
                name="BaseHandler", file="base.py"
            )
        ]
        mock_analyzer._children = [
            pytest.importorskip("core.models").HierarchyNode(
                name="SpecialHandler", file="special.py"
            )
        ]

        service = GraphAnalyzerService(analyzer=mock_analyzer)

        result = await service.get_class_hierarchy(
            org_id="test-org",
            class_name="OrderHandler",
            repo="api-service",
        )

        assert result.class_name == "OrderHandler"
        assert len(result.parents) > 0
        assert len(result.children) > 0


class TestRelatedEntitiesBehavior:
    """Test related entities query behavior."""

    @pytest.mark.asyncio
    async def test_related_entities_returns_relationships(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Related entities query should return relationship map."""
        service = GraphAnalyzerService(analyzer=mock_analyzer)

        result = await service.get_related_entities(
            org_id="test-org",
            entity="process_order",
            entity_type="function",
            relationship="all",
        )

        assert result.entity == "process_order"
        assert result.entity_type == "function"
        assert isinstance(result.relationships, dict)


class TestBatchOperationsBehavior:
    """Test batch operations behavior."""

    @pytest.mark.asyncio
    async def test_batch_related_returns_results_for_all_entities(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Batch query should return results for all requested entities."""
        service = GraphAnalyzerService(
            analyzer=mock_analyzer,
            feature_flags=FeatureFlags(enable_batch=True),
        )

        entities = [
            {"name": "process_order", "type": "function"},
            {"name": "OrderHandler", "type": "class"},
        ]

        results = await service.batch_related_entities(
            org_id="test-org",
            entities=entities,
            depth=1,
        )

        assert "process_order" in results
        assert "OrderHandler" in results

    @pytest.mark.asyncio
    async def test_batch_disabled_returns_empty(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Disabled batch should return empty results."""
        service = GraphAnalyzerService(
            analyzer=mock_analyzer,
            feature_flags=FeatureFlags(enable_batch=False),
        )

        results = await service.batch_related_entities(
            org_id="test-org",
            entities=[{"name": "test", "type": "function"}],
            depth=1,
        )

        assert results == {}


class TestCachingBehavior:
    """Test caching behavior."""

    @pytest.mark.asyncio
    async def test_cached_dependencies_returned_on_repeat_query(
        self,
        mock_analyzer: MockGraphAnalyzer,
        mock_cache: MockCache,
    ):
        """Repeat queries should return cached results."""
        service = GraphAnalyzerService(
            analyzer=mock_analyzer,
            cache=mock_cache,
            feature_flags=FeatureFlags(enable_caching=True),
        )

        await service.query_dependencies(
            org_id="test-org",
            repo="api-service",
            file_path="src/orders.py",
            depth=3,
        )
        first_call_count = len(mock_analyzer.calls)

        await service.query_dependencies(
            org_id="test-org",
            repo="api-service",
            file_path="src/orders.py",
            depth=3,
        )

        assert len(mock_analyzer.calls) == first_call_count


class TestHealthCheckBehavior:
    """Test health check behavior."""

    @pytest.mark.asyncio
    async def test_healthy_when_analyzer_available(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Service should be healthy when analyzer is available."""
        mock_analyzer._is_available = True
        service = GraphAnalyzerService(analyzer=mock_analyzer)

        is_healthy = await service.is_healthy()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_unhealthy_when_analyzer_unavailable(
        self,
        mock_analyzer: MockGraphAnalyzer,
    ):
        """Service should be unhealthy when analyzer is unavailable."""
        mock_analyzer._is_available = False
        service = GraphAnalyzerService(analyzer=mock_analyzer)

        is_healthy = await service.is_healthy()

        assert is_healthy is False
