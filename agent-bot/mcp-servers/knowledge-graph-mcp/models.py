from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    collection: str = "default"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(strict=True)

    query: str
    n_results: int = Field(default=5, ge=1, le=100)
    collection: str = "default"
    filter_metadata: dict[str, str] | None = None


class KnowledgeResult(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    content: str
    metadata: dict[str, Any]
    distance: float
    collection: str


class StoreResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    id: str
    collection: str
    message: str


class QueryResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    results: list[KnowledgeResult]
    query: str
    collection: str
    count: int


class CollectionInfo(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    count: int


class CollectionsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    collections: list[CollectionInfo]
    action: str
    message: str
