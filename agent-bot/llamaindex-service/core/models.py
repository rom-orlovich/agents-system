from pydantic import BaseModel, ConfigDict
from typing import Literal


class SearchResult(BaseModel):
    """Domain model for search results."""

    model_config = ConfigDict(strict=True)

    content: str
    source_type: Literal["code", "jira", "confluence", "github_issues"]
    source_id: str
    relevance_score: float
    metadata: dict[str, str | int | float | list[str]]


class GraphEntity(BaseModel):
    """Domain model for graph entities."""

    model_config = ConfigDict(strict=True)

    name: str
    entity_type: str
    file_path: str | None = None
    line_number: int | None = None
    metadata: dict[str, str | int] = {}


class QueryRequest(BaseModel):
    """Request model for queries."""

    model_config = ConfigDict(strict=True)

    query: str
    org_id: str
    source_types: list[str] | None = None
    top_k: int = 10
    include_metadata: bool = True
    filters: dict[str, str] | None = None


class CodeQueryRequest(BaseModel):
    """Request model for code queries."""

    model_config = ConfigDict(strict=True)

    query: str
    org_id: str
    repo_filter: str = "*"
    language: str = "*"
    top_k: int = 10


class TicketQueryRequest(BaseModel):
    """Request model for ticket queries."""

    model_config = ConfigDict(strict=True)

    query: str
    org_id: str
    project: str = "*"
    status: str = "*"
    top_k: int = 10


class DocsQueryRequest(BaseModel):
    """Request model for documentation queries."""

    model_config = ConfigDict(strict=True)

    query: str
    org_id: str
    space: str = "*"
    top_k: int = 10


class GraphRelatedRequest(BaseModel):
    """Request model for graph relationship queries."""

    model_config = ConfigDict(strict=True)

    entity: str
    entity_type: Literal["function", "class", "module", "file"]
    org_id: str
    relationship: str = "all"


class QueryResponse(BaseModel):
    """Response model for queries."""

    model_config = ConfigDict(strict=True)

    results: list[SearchResult]
    query: str
    total_results: int
    source_types_queried: list[str]
    cached: bool = False
    query_time_ms: float = 0.0


class GraphRelatedResponse(BaseModel):
    """Response model for graph queries."""

    model_config = ConfigDict(strict=True)

    entity: str
    entity_type: str
    relationships: dict[str, list[GraphEntity]]


class HealthStatus(BaseModel):
    """Health check response."""

    model_config = ConfigDict(strict=True)

    status: Literal["healthy", "degraded", "unhealthy"]
    vector_store: Literal["connected", "disconnected"]
    graph_store: Literal["connected", "disconnected", "disabled"]
    cache: Literal["connected", "disconnected", "disabled"]
    collections: list[str] = []
