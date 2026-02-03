import pytest

from core.models import (
    DependencyResult,
    DependencyItem,
    UsageResult,
    CallGraphResult,
    CallGraphNode,
    HierarchyResult,
    HierarchyNode,
    RelatedEntitiesResult,
    RelatedEntity,
)


class MockGraphAnalyzer:
    """Mock graph analyzer for testing."""

    def __init__(
        self,
        dependencies: list[DependencyItem] | None = None,
        usages: list[UsageResult] | None = None,
        callers: list[CallGraphNode] | None = None,
        callees: list[CallGraphNode] | None = None,
        parents: list[HierarchyNode] | None = None,
        children: list[HierarchyNode] | None = None,
        relationships: dict[str, list[RelatedEntity]] | None = None,
    ):
        self._dependencies = dependencies or []
        self._usages = usages or []
        self._callers = callers or []
        self._callees = callees or []
        self._parents = parents or []
        self._children = children or []
        self._relationships = relationships or {}
        self._is_available = True
        self._indexed_count = 5
        self._calls: list[dict] = []

    async def query_dependencies(
        self,
        org_id: str,
        repo: str,
        file_path: str,
        depth: int,
    ) -> DependencyResult:
        self._calls.append(
            {
                "method": "query_dependencies",
                "org_id": org_id,
                "repo": repo,
                "file_path": file_path,
                "depth": depth,
            }
        )
        return DependencyResult(
            file_path=file_path,
            repo=repo,
            dependencies=self._dependencies,
            formatted_output=f"Dependencies for {file_path}",
        )

    async def find_usages(
        self,
        org_id: str,
        symbol: str,
        repo: str,
    ) -> list[UsageResult]:
        self._calls.append(
            {
                "method": "find_usages",
                "org_id": org_id,
                "symbol": symbol,
                "repo": repo,
            }
        )
        return self._usages

    async def get_call_graph(
        self,
        org_id: str,
        repo: str,
        function_name: str,
        direction: str,
        depth: int,
    ) -> CallGraphResult:
        self._calls.append(
            {
                "method": "get_call_graph",
                "org_id": org_id,
                "function_name": function_name,
                "direction": direction,
            }
        )
        return CallGraphResult(
            function_name=function_name,
            callers=self._callers if direction in ("callers", "both") else [],
            callees=self._callees if direction in ("callees", "both") else [],
            formatted_graph=f"Call graph for {function_name}",
        )

    async def get_class_hierarchy(
        self,
        org_id: str,
        class_name: str,
        repo: str,
    ) -> HierarchyResult:
        self._calls.append(
            {
                "method": "get_class_hierarchy",
                "org_id": org_id,
                "class_name": class_name,
            }
        )
        return HierarchyResult(
            class_name=class_name,
            parents=self._parents,
            children=self._children,
            formatted_hierarchy=f"Hierarchy for {class_name}",
        )

    async def get_related_entities(
        self,
        org_id: str,
        entity: str,
        entity_type: str,
        relationship: str,
    ) -> RelatedEntitiesResult:
        self._calls.append(
            {
                "method": "get_related_entities",
                "org_id": org_id,
                "entity": entity,
                "entity_type": entity_type,
                "relationship": relationship,
            }
        )
        return RelatedEntitiesResult(
            entity=entity,
            entity_type=entity_type,
            relationships=self._relationships,
        )

    async def index_repo(self, org_id: str, repo_path: str) -> bool:
        self._calls.append(
            {
                "method": "index_repo",
                "org_id": org_id,
                "repo_path": repo_path,
            }
        )
        return True

    async def is_available(self) -> bool:
        return self._is_available

    async def get_indexed_count(self, org_id: str | None = None) -> int:
        return self._indexed_count

    @property
    def calls(self) -> list[dict]:
        return self._calls


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


@pytest.fixture
def sample_dependencies() -> list[DependencyItem]:
    return [
        DependencyItem(path="utils/helpers.py", type="module"),
        DependencyItem(path="models/user.py", type="module"),
    ]


@pytest.fixture
def sample_callers() -> list[CallGraphNode]:
    return [
        CallGraphNode(name="handle_request", file="handlers.py", line=50),
        CallGraphNode(name="main", file="app.py", line=10),
    ]


@pytest.fixture
def sample_callees() -> list[CallGraphNode]:
    return [
        CallGraphNode(name="validate", file="validators.py", line=25),
        CallGraphNode(name="save", file="database.py", line=100),
    ]


@pytest.fixture
def sample_relationships() -> dict[str, list[RelatedEntity]]:
    return {
        "calls": [
            RelatedEntity(name="validate_order", file="validators.py", line=15),
        ],
        "imports": [
            RelatedEntity(name="Order", file="models.py", line=5),
        ],
    }


@pytest.fixture
def mock_analyzer(
    sample_dependencies: list[DependencyItem],
    sample_callers: list[CallGraphNode],
    sample_callees: list[CallGraphNode],
    sample_relationships: dict[str, list[RelatedEntity]],
) -> MockGraphAnalyzer:
    return MockGraphAnalyzer(
        dependencies=sample_dependencies,
        callers=sample_callers,
        callees=sample_callees,
        relationships=sample_relationships,
    )


@pytest.fixture
def mock_cache() -> MockCache:
    return MockCache()
