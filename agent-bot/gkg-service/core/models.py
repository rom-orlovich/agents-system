from pydantic import BaseModel, ConfigDict
from typing import Literal


class DependencyItem(BaseModel):
    """A single dependency item."""

    model_config = ConfigDict(strict=True)

    path: str
    type: str
    line: int | None = None


class DependencyResult(BaseModel):
    """Result of dependency analysis."""

    model_config = ConfigDict(strict=True)

    file_path: str
    repo: str
    dependencies: list[DependencyItem]
    formatted_output: str


class UsageResult(BaseModel):
    """A single usage location."""

    model_config = ConfigDict(strict=True)

    file: str
    line: int
    context: str = ""


class CallGraphNode(BaseModel):
    """A node in the call graph."""

    model_config = ConfigDict(strict=True)

    name: str
    file: str
    line: int | None = None


class CallGraphResult(BaseModel):
    """Result of call graph analysis."""

    model_config = ConfigDict(strict=True)

    function_name: str
    callers: list[CallGraphNode]
    callees: list[CallGraphNode]
    formatted_graph: str


class HierarchyNode(BaseModel):
    """A node in class hierarchy."""

    model_config = ConfigDict(strict=True)

    name: str
    file: str


class HierarchyResult(BaseModel):
    """Result of hierarchy analysis."""

    model_config = ConfigDict(strict=True)

    class_name: str
    parents: list[HierarchyNode]
    children: list[HierarchyNode]
    formatted_hierarchy: str


class RelatedEntity(BaseModel):
    """A related entity."""

    model_config = ConfigDict(strict=True)

    name: str
    file: str
    line: int | None = None


class RelatedEntitiesResult(BaseModel):
    """Result of related entities query."""

    model_config = ConfigDict(strict=True)

    entity: str
    entity_type: str
    relationships: dict[str, list[RelatedEntity]]


class DependencyRequest(BaseModel):
    """Request for dependency analysis."""

    model_config = ConfigDict(strict=True)

    file_path: str
    org_id: str
    repo: str
    depth: int = 3


class UsageRequest(BaseModel):
    """Request for usage search."""

    model_config = ConfigDict(strict=True)

    symbol: str
    org_id: str
    repo: str = "*"


class CallGraphRequest(BaseModel):
    """Request for call graph."""

    model_config = ConfigDict(strict=True)

    function_name: str
    org_id: str
    repo: str
    direction: Literal["callers", "callees", "both"] = "both"
    depth: int = 2


class HierarchyRequest(BaseModel):
    """Request for class hierarchy."""

    model_config = ConfigDict(strict=True)

    class_name: str
    org_id: str
    repo: str = "*"


class RelatedRequest(BaseModel):
    """Request for related entities."""

    model_config = ConfigDict(strict=True)

    entity: str
    entity_type: Literal["function", "class", "module", "file"]
    org_id: str
    relationship: str = "all"


class BatchRelatedRequest(BaseModel):
    """Request for batch related entities."""

    model_config = ConfigDict(strict=True)

    entities: list[dict[str, str]]
    org_id: str
    depth: int = 1


class IndexRequest(BaseModel):
    """Request to index a repository."""

    model_config = ConfigDict(strict=True)

    repo_path: str
    org_id: str


class HealthStatus(BaseModel):
    """Service health status."""

    model_config = ConfigDict(strict=True)

    status: Literal["healthy", "unhealthy"]
    analyzer: Literal["available", "unavailable"]
    indexed_repos: int
