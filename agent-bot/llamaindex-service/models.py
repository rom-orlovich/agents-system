from pydantic import BaseModel, ConfigDict
from typing import Literal


class QueryRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    query: str
    org_id: str
    source_types: list[str] | None = None
    top_k: int = 10
    include_metadata: bool = True
    filters: dict[str, str] | None = None


class CodeQueryRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    query: str
    org_id: str
    filters: dict[str, str] | None = None
    top_k: int = 10


class TicketQueryRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    query: str
    org_id: str
    filters: dict[str, str] | None = None
    top_k: int = 10


class DocsQueryRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    query: str
    org_id: str
    filters: dict[str, str] | None = None
    top_k: int = 10


class GraphRelatedRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    entity: str
    entity_type: Literal["function", "class", "module", "file"]
    org_id: str
    relationship: str = "all"


class SearchResult(BaseModel):
    model_config = ConfigDict(strict=True)

    content: str
    source_type: str
    source_id: str
    relevance_score: float
    metadata: dict[str, str | int | float | list[str]]


class QueryResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    results: list[SearchResult]
    query: str
    total_results: int
    source_types_queried: list[str]


class GraphRelatedResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    entity: str
    entity_type: str
    relationships: dict[str, list[dict[str, str | int]]]


class HealthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    status: Literal["healthy", "unhealthy"]
    chromadb: Literal["connected", "disconnected"]
    gkg: Literal["connected", "disconnected"]
    collections: list[str]


class CollectionInfo(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    count: int
    metadata: dict[str, str | int]
