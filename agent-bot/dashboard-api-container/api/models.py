from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List


class TaskLogEntry(BaseModel):
    model_config = ConfigDict(strict=True)

    timestamp: str
    stage: str
    data: dict[str, str | int | bool | float]


class TaskLogsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    task_id: str
    metadata: dict[str, str | int | bool] | None = Field(None)
    input_data: dict[str, str | dict] | None = Field(None)
    webhook_flow: List[TaskLogEntry] = Field(default_factory=list)
    queue_flow: List[TaskLogEntry] = Field(default_factory=list)
    agent_output: List[TaskLogEntry] = Field(default_factory=list)
    microservices_flow: List[TaskLogEntry] = Field(default_factory=list)
    final_result: dict[str, str | bool | dict] | None = Field(None)


class AnalyticsMetrics(BaseModel):
    model_config = ConfigDict(strict=True)

    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    queued_tasks: int
    processing_tasks: int
    average_execution_time_seconds: float
    total_cost_usd: float
    success_rate: float


class ServiceMetrics(BaseModel):
    model_config = ConfigDict(strict=True)

    service_name: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    average_duration_ms: float
    success_rate: float


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    period_start: datetime
    period_end: datetime
    overall_metrics: AnalyticsMetrics
    service_metrics: List[ServiceMetrics]


class TaskListItem(BaseModel):
    model_config = ConfigDict(strict=True)

    task_id: str
    user_id: str
    input_message: str
    status: str
    created_at: datetime
    completed_at: datetime | None


class TaskListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    tasks: List[TaskListItem]
    total: int
    page: int
    page_size: int
