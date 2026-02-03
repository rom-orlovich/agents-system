import pytest

from core.models import SearchResult, GraphEntity


class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self, results: list[SearchResult] | None = None):
        self._results = results or []
        self._collections = ["code", "jira_tickets", "confluence_docs"]
        self._query_calls: list[dict] = []

    async def query(
        self,
        query_text: str,
        collection: str,
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[SearchResult]:
        self._query_calls.append(
            {
                "query_text": query_text,
                "collection": collection,
                "top_k": top_k,
                "filters": filters,
            }
        )
        return [
            r
            for r in self._results
            if r.source_type == self._map_collection(collection)
        ][:top_k]

    async def list_collections(self) -> list[str]:
        return self._collections

    async def health_check(self) -> bool:
        return True

    async def initialize(self) -> None:
        pass

    def _map_collection(self, collection: str) -> str:
        mapping = {
            "code": "code",
            "jira_tickets": "jira",
            "confluence_docs": "confluence",
        }
        return mapping.get(collection, collection)

    @property
    def query_calls(self) -> list[dict]:
        return self._query_calls


class MockGraphStore:
    """Mock graph store for testing."""

    def __init__(self, relationships: dict | None = None):
        self._relationships = relationships or {}
        self._calls: list[dict] = []

    async def get_related_entities(
        self,
        entity: str,
        entity_type: str,
        relationship: str,
        org_id: str,
    ) -> dict[str, list[GraphEntity]]:
        self._calls.append(
            {
                "entity": entity,
                "entity_type": entity_type,
                "relationship": relationship,
                "org_id": org_id,
            }
        )
        return self._relationships

    async def get_dependencies(
        self,
        file_path: str,
        org_id: str,
        depth: int,
    ) -> list[GraphEntity]:
        return []

    async def health_check(self) -> bool:
        return True


class MockCache:
    """Mock cache for testing."""

    def __init__(self):
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def health_check(self) -> bool:
        return True


@pytest.fixture
def sample_code_results() -> list[SearchResult]:
    return [
        SearchResult(
            content="def process_order(order_id): ...",
            source_type="code",
            source_id="repo1/orders.py:42",
            relevance_score=0.95,
            metadata={
                "repo": "api-service",
                "language": "python",
                "name": "process_order",
            },
        ),
        SearchResult(
            content="class OrderProcessor: ...",
            source_type="code",
            source_id="repo1/processor.py:10",
            relevance_score=0.88,
            metadata={
                "repo": "api-service",
                "language": "python",
                "name": "OrderProcessor",
            },
        ),
    ]


@pytest.fixture
def sample_ticket_results() -> list[SearchResult]:
    return [
        SearchResult(
            content="Bug: Order processing fails for international orders",
            source_type="jira",
            source_id="PROJ-123",
            relevance_score=0.92,
            metadata={"project": "PROJ", "status": "Open", "type": "Bug"},
        ),
    ]


@pytest.fixture
def sample_doc_results() -> list[SearchResult]:
    return [
        SearchResult(
            content="# Order Processing Guide\n\nThis document describes...",
            source_type="confluence",
            source_id="page-456",
            relevance_score=0.85,
            metadata={"space": "ENG", "title": "Order Processing Guide"},
        ),
    ]


@pytest.fixture
def mock_vector_store(
    sample_code_results: list[SearchResult],
    sample_ticket_results: list[SearchResult],
    sample_doc_results: list[SearchResult],
) -> MockVectorStore:
    all_results = sample_code_results + sample_ticket_results + sample_doc_results
    return MockVectorStore(results=all_results)


@pytest.fixture
def mock_graph_store() -> MockGraphStore:
    relationships = {
        "calls": [
            GraphEntity(
                name="validate_order",
                entity_type="function",
                file_path="validators.py",
                line_number=15,
            ),
        ],
        "called_by": [
            GraphEntity(
                name="handle_request",
                entity_type="function",
                file_path="handlers.py",
                line_number=50,
            ),
        ],
    }
    return MockGraphStore(relationships=relationships)


@pytest.fixture
def mock_cache() -> MockCache:
    return MockCache()
