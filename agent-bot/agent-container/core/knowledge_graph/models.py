from enum import Enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntityType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    MODULE = "module"
    IMPORT = "import"
    TEST = "test"


class RelationType(str, Enum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    CALLS = "calls"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    TESTS = "tests"
    DEPENDS_ON = "depends_on"


class Entity(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    type: EntityType
    name: str
    file_path: str
    line_number: int | None = None
    end_line_number: int | None = None
    metadata: dict[str, str] = {}


class Relation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source_id: str
    target_id: str
    type: RelationType
    metadata: dict[str, str] = {}


class IndexResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    repo_path: str
    commit_hash: str
    entities_count: int
    relations_count: int
    indexed_at: datetime
    duration_seconds: float


class FunctionCallers(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    function_name: str
    callers: list[Entity]


class ClassHierarchy(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    class_name: str
    parents: list[Entity]
    children: list[Entity]


class ImpactAnalysis(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    file_path: str
    affected_files: list[str]
    affected_tests: list[str]
    risk_score: float
