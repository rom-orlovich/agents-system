from dataclasses import dataclass

from core.interfaces import GraphAnalyzerProtocol, CacheProtocol
from core.models import (
    DependencyResult,
    CallGraphResult,
    HierarchyResult,
    RelatedEntitiesResult,
    UsageResult,
    RelatedEntity,
)


@dataclass
class FeatureFlags:
    """Feature flags for graph analyzer."""

    enable_caching: bool = True
    cache_ttl_seconds: int = 600
    enable_batch: bool = True
    max_batch_size: int = 50


class GraphAnalyzerService:
    """
    Core graph analysis service.

    Orchestrates graph queries with optional caching.
    All external dependencies are injected via protocols.
    """

    def __init__(
        self,
        analyzer: GraphAnalyzerProtocol,
        cache: CacheProtocol | None = None,
        feature_flags: FeatureFlags | None = None,
    ):
        self._analyzer = analyzer
        self._cache = cache
        self._flags = feature_flags or FeatureFlags()

    async def query_dependencies(
        self,
        org_id: str,
        repo: str,
        file_path: str,
        depth: int = 3,
    ) -> DependencyResult:
        """Query file dependencies with optional caching."""
        cache_key = f"deps:{org_id}:{repo}:{file_path}:{depth}"

        if self._flags.enable_caching and self._cache:
            cached = await self._cache.get(cache_key)
            if cached:
                return DependencyResult.model_validate_json(cached)

        result = await self._analyzer.query_dependencies(
            org_id=org_id,
            repo=repo,
            file_path=file_path,
            depth=depth,
        )

        if self._flags.enable_caching and self._cache:
            await self._cache.set(
                cache_key,
                result.model_dump_json(),
                self._flags.cache_ttl_seconds,
            )

        return result

    async def find_usages(
        self,
        org_id: str,
        symbol: str,
        repo: str = "*",
    ) -> list[UsageResult]:
        """Find symbol usages."""
        return await self._analyzer.find_usages(
            org_id=org_id,
            symbol=symbol,
            repo=repo,
        )

    async def get_call_graph(
        self,
        org_id: str,
        repo: str,
        function_name: str,
        direction: str = "both",
        depth: int = 2,
    ) -> CallGraphResult:
        """Get function call graph."""
        return await self._analyzer.get_call_graph(
            org_id=org_id,
            repo=repo,
            function_name=function_name,
            direction=direction,
            depth=depth,
        )

    async def get_class_hierarchy(
        self,
        org_id: str,
        class_name: str,
        repo: str = "*",
    ) -> HierarchyResult:
        """Get class inheritance hierarchy."""
        return await self._analyzer.get_class_hierarchy(
            org_id=org_id,
            class_name=class_name,
            repo=repo,
        )

    async def get_related_entities(
        self,
        org_id: str,
        entity: str,
        entity_type: str,
        relationship: str = "all",
    ) -> RelatedEntitiesResult:
        """Get related code entities."""
        return await self._analyzer.get_related_entities(
            org_id=org_id,
            entity=entity,
            entity_type=entity_type,
            relationship=relationship,
        )

    async def batch_related_entities(
        self,
        org_id: str,
        entities: list[dict[str, str]],
        depth: int = 1,
    ) -> dict[str, dict[str, list[RelatedEntity]]]:
        """Batch query for related entities."""
        if not self._flags.enable_batch:
            return {}

        entities_to_process = entities[: self._flags.max_batch_size]
        results: dict[str, dict[str, list[RelatedEntity]]] = {}

        for entity in entities_to_process:
            name = entity.get("name", "")
            entity_type = entity.get("type", "function")
            if name:
                related = await self._analyzer.get_related_entities(
                    org_id=org_id,
                    entity=name,
                    entity_type=entity_type,
                    relationship="all",
                )
                results[name] = {k: v for k, v in related.relationships.items()}

        return results

    async def index_repo(self, org_id: str, repo_path: str) -> bool:
        """Index a repository for analysis."""
        return await self._analyzer.index_repo(
            org_id=org_id,
            repo_path=repo_path,
        )

    async def is_healthy(self) -> bool:
        """Check if the analyzer is available."""
        return await self._analyzer.is_available()

    async def get_indexed_count(self, org_id: str | None = None) -> int:
        """Get count of indexed repositories."""
        return await self._analyzer.get_indexed_count(org_id)
