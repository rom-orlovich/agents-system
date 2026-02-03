from pydantic import BaseModel, ConfigDict
from typing import Literal


class DependencyRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    file_path: str
    org_id: str
    repo: str
    depth: int = 3


class UsageRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    symbol: str
    org_id: str
    repo: str = "*"


class CallGraphRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    function_name: str
    org_id: str
    repo: str
    direction: Literal["callers", "callees", "both"] = "both"
    depth: int = 2


class HierarchyRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    class_name: str
    org_id: str
    repo: str = "*"


class RelatedRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    entity: str
    entity_type: Literal["function", "class", "module", "file"]
    org_id: str
    relationship: str = "all"


class BatchRelatedRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    entities: list[dict[str, str]]
    org_id: str
    depth: int = 1


class IndexRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    repo_path: str
    org_id: str


class DependencyResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    file_path: str
    repo: str
    dependencies: list[dict[str, str | int]]
    formatted_output: str


class UsageResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    symbol: str
    usages: list[dict[str, str | int]]


class CallGraphResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    function_name: str
    callers: list[dict[str, str | int]]
    callees: list[dict[str, str | int]]
    formatted_graph: str


class HierarchyResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    class_name: str
    parents: list[dict[str, str]]
    children: list[dict[str, str]]
    formatted_hierarchy: str


class RelatedResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    entity: str
    entity_type: str
    relationships: dict[str, list[dict[str, str | int]]]


class HealthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    status: Literal["healthy", "unhealthy"]
    gkg_binary: Literal["available", "missing"]
    indexed_repos: int
