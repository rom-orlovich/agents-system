from typing import Protocol, runtime_checkable
from core.models import (
    DependencyResult,
    UsageResult,
    CallGraphResult,
    HierarchyResult,
    RelatedEntitiesResult,
)


@runtime_checkable
class GraphAnalyzerProtocol(Protocol):
    """Protocol for graph analysis implementations (GKG, Neo4j, etc.)."""

    async def query_dependencies(
        self,
        org_id: str,
        repo: str,
        file_path: str,
        depth: int,
    ) -> DependencyResult:
        """Query file dependencies."""
        ...

    async def find_usages(
        self,
        org_id: str,
        symbol: str,
        repo: str,
    ) -> list[UsageResult]:
        """Find symbol usages across codebase."""
        ...

    async def get_call_graph(
        self,
        org_id: str,
        repo: str,
        function_name: str,
        direction: str,
        depth: int,
    ) -> CallGraphResult:
        """Get function call graph."""
        ...

    async def get_class_hierarchy(
        self,
        org_id: str,
        class_name: str,
        repo: str,
    ) -> HierarchyResult:
        """Get class inheritance hierarchy."""
        ...

    async def get_related_entities(
        self,
        org_id: str,
        entity: str,
        entity_type: str,
        relationship: str,
    ) -> RelatedEntitiesResult:
        """Find related code entities."""
        ...

    async def index_repo(
        self,
        org_id: str,
        repo_path: str,
    ) -> bool:
        """Index a repository for graph queries."""
        ...

    async def is_available(self) -> bool:
        """Check if analyzer is available."""
        ...

    async def get_indexed_count(self, org_id: str | None = None) -> int:
        """Get count of indexed repositories."""
        ...


@runtime_checkable
class CacheProtocol(Protocol):
    """Protocol for caching query results."""

    async def get(self, key: str) -> str | None:
        """Get cached value."""
        ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Set cached value."""
        ...

    async def delete(self, key: str) -> None:
        """Delete cached value."""
        ...
