from pydantic import BaseModel, ConfigDict
from typing import Literal
from datetime import datetime


class IndexJobRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    org_id: str
    source_id: str | None = None
    job_type: Literal["full", "incremental", "delete"] = "incremental"


class GitHubSourceConfig(BaseModel):
    model_config = ConfigDict(strict=True)

    include_patterns: list[str] = []
    exclude_patterns: list[str] = []
    topics: list[str] = []
    languages: list[str] = []
    branches: list[str] = ["main", "master"]
    file_patterns: list[str] = ["**/*.py", "**/*.ts", "**/*.js", "**/*.go"]
    exclude_file_patterns: list[str] = ["**/node_modules/**", "**/__pycache__/**"]


class JiraSourceConfig(BaseModel):
    model_config = ConfigDict(strict=True)

    jql: str = ""
    issue_types: list[str] = ["Bug", "Story", "Task"]
    include_labels: list[str] = []
    exclude_labels: list[str] = []
    max_results: int = 1000


class ConfluenceSourceConfig(BaseModel):
    model_config = ConfigDict(strict=True)

    spaces: list[str] = []
    include_labels: list[str] = []
    exclude_labels: list[str] = []
    content_types: list[str] = ["page", "blogpost"]


class DataSourceConfig(BaseModel):
    model_config = ConfigDict(strict=True)

    source_id: str
    org_id: str
    source_type: Literal["github", "jira", "confluence"]
    name: str
    enabled: bool = True
    config: GitHubSourceConfig | JiraSourceConfig | ConfluenceSourceConfig


class IndexJobStatus(BaseModel):
    model_config = ConfigDict(strict=True)

    job_id: str
    org_id: str
    source_id: str | None
    job_type: str
    status: Literal["queued", "running", "completed", "failed"]
    progress_percent: int = 0
    items_total: int = 0
    items_processed: int = 0
    items_failed: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CodeChunk(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    content: str
    repo: str
    file_path: str
    language: str
    chunk_type: Literal["function", "class", "module", "docstring", "other"]
    name: str | None = None
    line_start: int
    line_end: int


class DocumentChunk(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    content: str
    source_type: Literal["jira", "confluence"]
    source_id: str
    title: str
    metadata: dict[str, str | int | list[str]]


class HealthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    status: Literal["healthy", "unhealthy"]
    chromadb: Literal["connected", "disconnected"]
    gkg: Literal["connected", "disconnected"]
    redis: Literal["connected", "disconnected"]
    active_jobs: int
