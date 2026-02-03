import os
import structlog

from core.interfaces import (
    VectorStoreProtocol,
    GraphStoreProtocol,
    CacheProtocol,
)
from core.query_engine import HybridQueryEngine, FeatureFlags
from adapters.chroma_adapter import ChromaVectorStore
from adapters.gkg_adapter import GKGGraphStore
from adapters.redis_cache_adapter import RedisCacheAdapter, InMemoryCacheAdapter

logger = structlog.get_logger()


class ServiceConfig:
    """Configuration for service dependencies."""

    chromadb_url: str = os.getenv("CHROMADB_URL", "http://chromadb:8000")
    gkg_url: str = os.getenv("GKG_URL", "http://gkg-service:8003")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8002"))

    enable_gkg: bool = os.getenv("ENABLE_GKG", "true").lower() == "true"
    enable_cache: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    enable_reranking: bool = os.getenv("ENABLE_RERANKING", "false").lower() == "true"
    cache_ttl: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))


class ServiceContainer:
    """
    Dependency injection container for service components.

    All components are instantiated lazily and can be replaced for testing.
    """

    def __init__(self, config: ServiceConfig | None = None):
        self._config = config or ServiceConfig()
        self._vector_store: VectorStoreProtocol | None = None
        self._graph_store: GraphStoreProtocol | None = None
        self._cache: CacheProtocol | None = None
        self._query_engine: HybridQueryEngine | None = None
        self._initialized = False

    @property
    def config(self) -> ServiceConfig:
        return self._config

    @property
    def vector_store(self) -> VectorStoreProtocol:
        if self._vector_store is None:
            raise RuntimeError("Container not initialized. Call initialize() first.")
        return self._vector_store

    @property
    def graph_store(self) -> GraphStoreProtocol | None:
        return self._graph_store

    @property
    def cache(self) -> CacheProtocol | None:
        return self._cache

    @property
    def query_engine(self) -> HybridQueryEngine:
        if self._query_engine is None:
            raise RuntimeError("Container not initialized. Call initialize() first.")
        return self._query_engine

    def set_vector_store(self, store: VectorStoreProtocol) -> None:
        """Override vector store (for testing)."""
        self._vector_store = store

    def set_graph_store(self, store: GraphStoreProtocol | None) -> None:
        """Override graph store (for testing)."""
        self._graph_store = store

    def set_cache(self, cache: CacheProtocol | None) -> None:
        """Override cache (for testing)."""
        self._cache = cache

    async def initialize(self) -> None:
        """Initialize all service components."""
        if self._initialized:
            return

        logger.info("service_container_initializing")

        if self._vector_store is None:
            self._vector_store = ChromaVectorStore(self._config.chromadb_url)
            await self._vector_store.initialize()

        if self._config.enable_gkg and self._graph_store is None:
            self._graph_store = GKGGraphStore(self._config.gkg_url)

        if self._config.enable_cache and self._cache is None:
            if self._config.redis_url:
                self._cache = RedisCacheAdapter(self._config.redis_url)
                await self._cache.initialize()
            else:
                self._cache = InMemoryCacheAdapter()

        feature_flags = FeatureFlags(
            enable_gkg_enrichment=self._config.enable_gkg
            and self._graph_store is not None,
            enable_caching=self._config.enable_cache and self._cache is not None,
            enable_reranking=self._config.enable_reranking,
            cache_ttl_seconds=self._config.cache_ttl,
        )

        self._query_engine = HybridQueryEngine(
            vector_store=self._vector_store,
            graph_store=self._graph_store,
            cache=self._cache,
            feature_flags=feature_flags,
        )

        self._initialized = True
        logger.info(
            "service_container_initialized",
            gkg_enabled=self._config.enable_gkg,
            cache_enabled=self._config.enable_cache,
        )

    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._cache and hasattr(self._cache, "close"):
            await self._cache.close()
        logger.info("service_container_shutdown")


def create_test_container(
    vector_store: VectorStoreProtocol | None = None,
    graph_store: GraphStoreProtocol | None = None,
    cache: CacheProtocol | None = None,
) -> ServiceContainer:
    """Create container with mock dependencies for testing."""
    config = ServiceConfig()
    config.enable_gkg = graph_store is not None
    config.enable_cache = cache is not None

    container = ServiceContainer(config)
    if vector_store:
        container.set_vector_store(vector_store)
    if graph_store:
        container.set_graph_store(graph_store)
    if cache:
        container.set_cache(cache)

    return container
