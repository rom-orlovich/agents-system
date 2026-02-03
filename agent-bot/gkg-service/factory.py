import os
import structlog

from core.interfaces import GraphAnalyzerProtocol, CacheProtocol
from core.graph_analyzer import GraphAnalyzerService, FeatureFlags
from adapters.gkg_binary_adapter import GKGBinaryAdapter

logger = structlog.get_logger()


class ServiceConfig:
    """Configuration for service dependencies."""

    gkg_binary: str = os.getenv("GKG_BINARY", "gkg")
    data_dir: str = os.getenv("DATA_DIR", "/data/gkg")
    repos_dir: str = os.getenv("REPOS_DIR", "/data/repos")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8003"))

    enable_caching: bool = os.getenv("ENABLE_CACHING", "false").lower() == "true"
    enable_batch: bool = os.getenv("ENABLE_BATCH", "true").lower() == "true"
    cache_ttl: int = int(os.getenv("CACHE_TTL_SECONDS", "600"))
    max_batch_size: int = int(os.getenv("MAX_BATCH_SIZE", "50"))


class ServiceContainer:
    """Dependency injection container for service components."""

    def __init__(self, config: ServiceConfig | None = None):
        self._config = config or ServiceConfig()
        self._analyzer: GraphAnalyzerProtocol | None = None
        self._cache: CacheProtocol | None = None
        self._service: GraphAnalyzerService | None = None
        self._initialized = False

    @property
    def config(self) -> ServiceConfig:
        return self._config

    @property
    def analyzer(self) -> GraphAnalyzerProtocol:
        if self._analyzer is None:
            raise RuntimeError("Container not initialized")
        return self._analyzer

    @property
    def service(self) -> GraphAnalyzerService:
        if self._service is None:
            raise RuntimeError("Container not initialized")
        return self._service

    def set_analyzer(self, analyzer: GraphAnalyzerProtocol) -> None:
        """Override analyzer (for testing)."""
        self._analyzer = analyzer

    def set_cache(self, cache: CacheProtocol | None) -> None:
        """Override cache (for testing)."""
        self._cache = cache

    async def initialize(self) -> None:
        """Initialize all service components."""
        if self._initialized:
            return

        logger.info("service_container_initializing")

        if self._analyzer is None:
            self._analyzer = GKGBinaryAdapter(
                binary_path=self._config.gkg_binary,
                data_dir=self._config.data_dir,
                repos_dir=self._config.repos_dir,
            )

        feature_flags = FeatureFlags(
            enable_caching=self._config.enable_caching and self._cache is not None,
            cache_ttl_seconds=self._config.cache_ttl,
            enable_batch=self._config.enable_batch,
            max_batch_size=self._config.max_batch_size,
        )

        self._service = GraphAnalyzerService(
            analyzer=self._analyzer,
            cache=self._cache,
            feature_flags=feature_flags,
        )

        self._initialized = True
        logger.info(
            "service_container_initialized",
            caching_enabled=self._config.enable_caching,
            batch_enabled=self._config.enable_batch,
        )

    async def shutdown(self) -> None:
        """Cleanup resources."""
        logger.info("service_container_shutdown")


def create_test_container(
    analyzer: GraphAnalyzerProtocol | None = None,
    cache: CacheProtocol | None = None,
) -> ServiceContainer:
    """Create container with mock dependencies for testing."""
    config = ServiceConfig()
    config.enable_caching = cache is not None

    container = ServiceContainer(config)
    if analyzer:
        container.set_analyzer(analyzer)
    if cache:
        container.set_cache(cache)

    return container
