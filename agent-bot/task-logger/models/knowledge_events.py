from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class KnowledgeEventType(StrEnum):
    QUERY_STARTED = "knowledge:query_started"
    QUERY_COMPLETED = "knowledge:query_completed"
    QUERY_FAILED = "knowledge:query_failed"
    CONTEXT_RETRIEVED = "knowledge:context_retrieved"
    CONTEXT_USED = "knowledge:context_used"
    GRAPH_TRAVERSAL = "knowledge:graph_traversal"
    VECTOR_SEARCH = "knowledge:vector_search"
    RELEVANCE_SCORE = "knowledge:relevance_score"


class KnowledgeQueryEvent(BaseModel):
    model_config = ConfigDict(strict=True)

    event_type: KnowledgeEventType
    task_id: str
    query: str
    org_id: str
    source_types: list[str]
    top_k: int = 10


class KnowledgeResultEvent(BaseModel):
    model_config = ConfigDict(strict=True)

    event_type: KnowledgeEventType
    task_id: str
    query: str
    result_count: int
    results: list[dict[str, Any]]
    query_time_ms: float
    cached: bool = False


class KnowledgeContextItem(BaseModel):
    model_config = ConfigDict(strict=True)

    source_type: str
    file_path: str | None = None
    line_number: int | None = None
    content_preview: str
    relevance_score: float
    metadata: dict[str, Any] = {}


class KnowledgeUsageEvent(BaseModel):
    model_config = ConfigDict(strict=True)

    event_type: KnowledgeEventType
    task_id: str
    tool_name: str
    query: str
    contexts_retrieved: list[KnowledgeContextItem]
    contexts_used_count: int
    total_tokens_added: int | None = None


class GraphTraversalEvent(BaseModel):
    model_config = ConfigDict(strict=True)

    event_type: KnowledgeEventType
    task_id: str
    start_node: str
    traversal_type: str
    depth: int
    nodes_visited: int
    edges_traversed: int
    results: list[dict[str, Any]]
