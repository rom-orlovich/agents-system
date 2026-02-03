import hashlib
import time
from dataclasses import dataclass

from core.interfaces import (
    VectorStoreProtocol,
    GraphStoreProtocol,
    CacheProtocol,
    RerankerProtocol,
)
from core.models import SearchResult, QueryResponse


@dataclass
class FeatureFlags:
    """Feature flags for query engine capabilities."""

    enable_gkg_enrichment: bool = True
    enable_reranking: bool = True
    enable_caching: bool = True
    cache_ttl_seconds: int = 300


SOURCE_TYPE_COLLECTION_MAP = {
    "code": "code",
    "jira": "jira_tickets",
    "confluence": "confluence_docs",
    "github_issues": "github_issues",
}


class HybridQueryEngine:
    """
    Orchestrates hybrid queries across vector and graph stores.

    This is the core business logic, independent of external frameworks.
    All dependencies are injected via protocols.
    """

    def __init__(
        self,
        vector_store: VectorStoreProtocol,
        graph_store: GraphStoreProtocol | None = None,
        cache: CacheProtocol | None = None,
        reranker: RerankerProtocol | None = None,
        feature_flags: FeatureFlags | None = None,
    ):
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._cache = cache
        self._reranker = reranker
        self._flags = feature_flags or FeatureFlags()

    async def query(
        self,
        query: str,
        org_id: str,
        source_types: list[str] | None = None,
        top_k: int = 10,
        include_metadata: bool = True,
    ) -> QueryResponse:
        """Execute hybrid query across multiple sources."""
        start_time = time.time()
        source_types = source_types or ["code", "jira", "confluence"]

        cache_key = self._generate_cache_key(query, org_id, source_types, top_k)
        if self._flags.enable_caching and self._cache:
            cached = await self._get_cached(cache_key)
            if cached:
                return cached

        results = await self._execute_vector_search(query, org_id, source_types, top_k)

        if (
            self._flags.enable_gkg_enrichment
            and self._graph_store
            and "code" in source_types
        ):
            results = await self._enrich_with_graph(query, results, org_id)

        if self._flags.enable_reranking and self._reranker and len(results) > top_k:
            results = self._apply_reranking(query, results, top_k)

        results = results[:top_k]
        query_time_ms = (time.time() - start_time) * 1000

        response = QueryResponse(
            results=results,
            query=query,
            total_results=len(results),
            source_types_queried=source_types,
            cached=False,
            query_time_ms=query_time_ms,
        )

        if self._flags.enable_caching and self._cache:
            await self._set_cached(cache_key, response)

        return response

    async def query_code(
        self,
        query: str,
        org_id: str,
        repo_filter: str = "*",
        language: str = "*",
        top_k: int = 10,
    ) -> QueryResponse:
        """Execute code-specific query."""
        start_time = time.time()

        filters = {"org_id": org_id}
        if repo_filter != "*":
            filters["repo"] = repo_filter
        if language != "*":
            filters["language"] = language

        results = await self._vector_store.query(
            query_text=query,
            collection="code",
            top_k=top_k,
            filters=filters,
        )

        query_time_ms = (time.time() - start_time) * 1000

        return QueryResponse(
            results=results,
            query=query,
            total_results=len(results),
            source_types_queried=["code"],
            query_time_ms=query_time_ms,
        )

    async def query_tickets(
        self,
        query: str,
        org_id: str,
        project: str = "*",
        status: str = "*",
        top_k: int = 10,
    ) -> QueryResponse:
        """Execute Jira ticket query."""
        start_time = time.time()

        filters = {"org_id": org_id}
        if project != "*":
            filters["project"] = project
        if status != "*":
            filters["status"] = status

        results = await self._vector_store.query(
            query_text=query,
            collection="jira_tickets",
            top_k=top_k,
            filters=filters,
        )

        query_time_ms = (time.time() - start_time) * 1000

        return QueryResponse(
            results=results,
            query=query,
            total_results=len(results),
            source_types_queried=["jira"],
            query_time_ms=query_time_ms,
        )

    async def query_docs(
        self,
        query: str,
        org_id: str,
        space: str = "*",
        top_k: int = 10,
    ) -> QueryResponse:
        """Execute Confluence documentation query."""
        start_time = time.time()

        filters = {"org_id": org_id}
        if space != "*":
            filters["space"] = space

        results = await self._vector_store.query(
            query_text=query,
            collection="confluence_docs",
            top_k=top_k,
            filters=filters,
        )

        query_time_ms = (time.time() - start_time) * 1000

        return QueryResponse(
            results=results,
            query=query,
            total_results=len(results),
            source_types_queried=["confluence"],
            query_time_ms=query_time_ms,
        )

    async def get_related_entities(
        self,
        entity: str,
        entity_type: str,
        org_id: str,
        relationship: str = "all",
    ) -> dict[str, list]:
        """Get related entities via graph store."""
        if not self._graph_store:
            return {}

        return await self._graph_store.get_related_entities(
            entity=entity,
            entity_type=entity_type,
            relationship=relationship,
            org_id=org_id,
        )

    async def _execute_vector_search(
        self,
        query: str,
        org_id: str,
        source_types: list[str],
        top_k: int,
    ) -> list[SearchResult]:
        """Execute vector search across specified collections."""
        results: list[SearchResult] = []

        for source_type in source_types:
            collection = SOURCE_TYPE_COLLECTION_MAP.get(source_type)
            if not collection:
                continue

            source_results = await self._vector_store.query(
                query_text=query,
                collection=collection,
                top_k=top_k,
                filters={"org_id": org_id},
            )
            results.extend(source_results)

        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results

    async def _enrich_with_graph(
        self,
        query: str,
        results: list[SearchResult],
        org_id: str,
    ) -> list[SearchResult]:
        """Enrich code results with graph context."""
        if not self._graph_store:
            return results

        code_results = [r for r in results if r.source_type == "code"]
        if not code_results:
            return results

        for result in code_results[:5]:
            entity_name = result.metadata.get("name")
            if entity_name and isinstance(entity_name, str):
                related = await self._graph_store.get_related_entities(
                    entity=entity_name,
                    entity_type=str(result.metadata.get("chunk_type", "function")),
                    relationship="all",
                    org_id=org_id,
                )
                if related:
                    result.metadata["graph_context"] = str(related)

        return results

    def _apply_reranking(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """Apply cross-encoder reranking."""
        if not self._reranker or len(results) <= top_k:
            return results

        documents = [r.content for r in results]
        reranked_indices = self._reranker.rerank(query, documents, top_k)

        return [results[idx] for idx, _ in reranked_indices]

    def _generate_cache_key(
        self,
        query: str,
        org_id: str,
        source_types: list[str],
        top_k: int,
    ) -> str:
        """Generate cache key for query."""
        key_str = f"{query}:{org_id}:{','.join(sorted(source_types))}:{top_k}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    async def _get_cached(self, key: str) -> QueryResponse | None:
        """Get cached query response."""
        if not self._cache:
            return None
        cached = await self._cache.get(key)
        if cached:
            return QueryResponse.model_validate_json(cached)
        return None

    async def _set_cached(self, key: str, response: QueryResponse) -> None:
        """Cache query response."""
        if not self._cache:
            return
        response.cached = True
        await self._cache.set(
            key, response.model_dump_json(), self._flags.cache_ttl_seconds
        )
