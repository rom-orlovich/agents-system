import pytest

from core.models import JobStatus, CodeChunk, DocumentChunk


class MockSourceIndexer:
    """Mock source indexer for testing."""

    def __init__(
        self,
        items: list[dict] | None = None,
        chunks: list | None = None,
    ):
        self._items = items or []
        self._chunks = chunks or []
        self._calls: list[dict] = []

    async def fetch_items(self) -> list[dict]:
        self._calls.append({"method": "fetch_items"})
        return self._items

    async def index_items(self, items: list[dict]) -> list:
        self._calls.append({"method": "index_items", "item_count": len(items)})
        return self._chunks


class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self):
        self._code_chunks: list = []
        self._doc_chunks: list = []
        self._calls: list[dict] = []

    async def upsert_code_chunks(
        self,
        org_id: str,
        chunks: list[CodeChunk],
        embeddings: list[list[float]],
    ) -> None:
        self._calls.append(
            {
                "method": "upsert_code_chunks",
                "org_id": org_id,
                "chunk_count": len(chunks),
            }
        )
        self._code_chunks.extend(chunks)

    async def upsert_document_chunks(
        self,
        org_id: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        collection: str,
    ) -> None:
        self._calls.append(
            {
                "method": "upsert_document_chunks",
                "org_id": org_id,
                "chunk_count": len(chunks),
                "collection": collection,
            }
        )
        self._doc_chunks.extend(chunks)

    async def health_check(self) -> bool:
        return True

    @property
    def calls(self) -> list[dict]:
        return self._calls


class MockGraphStore:
    """Mock graph store for testing."""

    def __init__(self):
        self._indexed_repos: list[str] = []
        self._calls: list[dict] = []

    async def index_repository(self, org_id: str, repo_path: str) -> bool:
        self._calls.append(
            {
                "method": "index_repository",
                "org_id": org_id,
                "repo_path": repo_path,
            }
        )
        self._indexed_repos.append(repo_path)
        return True

    async def health_check(self) -> bool:
        return True


class MockEmbeddingProvider:
    """Mock embedding provider for testing."""

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self._dimension for _ in texts]


class MockJobQueue:
    """Mock job queue for testing."""

    def __init__(self):
        self._statuses: list[JobStatus] = []
        self._completions: list[JobStatus] = []

    async def pop_job(self, timeout: int) -> dict | None:
        return None

    async def update_status(self, status: JobStatus) -> None:
        self._statuses.append(status)

    async def publish_completion(self, status: JobStatus) -> None:
        self._completions.append(status)

    async def health_check(self) -> bool:
        return True

    @property
    def statuses(self) -> list[JobStatus]:
        return self._statuses

    @property
    def completions(self) -> list[JobStatus]:
        return self._completions


class MockSourceFetcher:
    """Mock source config fetcher for testing."""

    def __init__(self, sources: list[dict] | None = None):
        self._sources = sources or []

    async def fetch_sources(
        self,
        org_id: str,
        source_id: str | None,
    ) -> list[dict]:
        return self._sources


@pytest.fixture
def sample_code_chunks() -> list[CodeChunk]:
    return [
        CodeChunk(
            id="chunk-1",
            content="def process_order(order_id): pass",
            repo="api-service",
            file_path="orders.py",
            language="python",
            chunk_type="function",
            name="process_order",
            line_start=1,
            line_end=10,
        ),
        CodeChunk(
            id="chunk-2",
            content="class OrderProcessor: pass",
            repo="api-service",
            file_path="processor.py",
            language="python",
            chunk_type="class",
            name="OrderProcessor",
            line_start=1,
            line_end=20,
        ),
    ]


@pytest.fixture
def sample_document_chunks() -> list[DocumentChunk]:
    return [
        DocumentChunk(
            id="doc-1",
            content="Bug: Order processing fails for large orders",
            source_type="jira",
            source_id="PROJ-123",
            title="Order Processing Bug",
            metadata={"project": "PROJ", "status": "Open"},
        ),
    ]


@pytest.fixture
def sample_source_config() -> list[dict]:
    return [
        {
            "source_id": "src-1",
            "org_id": "test-org",
            "source_type": "github",
            "name": "API Service",
            "enabled": True,
            "config_json": '{"include_patterns": ["owner/repo"]}',
        }
    ]


@pytest.fixture
def mock_vector_store() -> MockVectorStore:
    return MockVectorStore()


@pytest.fixture
def mock_graph_store() -> MockGraphStore:
    return MockGraphStore()


@pytest.fixture
def mock_embedding() -> MockEmbeddingProvider:
    return MockEmbeddingProvider()


@pytest.fixture
def mock_queue() -> MockJobQueue:
    return MockJobQueue()


@pytest.fixture
def mock_source_fetcher(sample_source_config: list[dict]) -> MockSourceFetcher:
    return MockSourceFetcher(sources=sample_source_config)
