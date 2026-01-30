from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime
from typing import List, Tuple
from api.models import (
    AnalyticsMetrics,
    ServiceMetrics,
    TaskListItem,
)
import structlog

logger = structlog.get_logger()


class AnalyticsRepository:
    def __init__(self):
        pass

    async def get_overall_metrics(
        self, period_start: datetime, period_end: datetime
    ) -> AnalyticsMetrics:
        return AnalyticsMetrics(
            total_tasks=100,
            completed_tasks=85,
            failed_tasks=10,
            queued_tasks=3,
            processing_tasks=2,
            average_execution_time_seconds=12.5,
            total_cost_usd=5.75,
            success_rate=0.85,
        )

    async def get_service_metrics(
        self, period_start: datetime, period_end: datetime
    ) -> List[ServiceMetrics]:
        return [
            ServiceMetrics(
                service_name="github",
                total_calls=150,
                successful_calls=145,
                failed_calls=5,
                average_duration_ms=125.5,
                success_rate=0.967,
            ),
            ServiceMetrics(
                service_name="jira",
                total_calls=80,
                successful_calls=78,
                failed_calls=2,
                average_duration_ms=200.3,
                success_rate=0.975,
            ),
        ]

    async def list_tasks(
        self,
        user_id: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> Tuple[List[TaskListItem], int]:
        tasks = [
            TaskListItem(
                task_id="task-123",
                user_id="user-456",
                input_message="analyze this issue",
                status="COMPLETED",
                created_at=datetime.now(),
                completed_at=datetime.now(),
            )
        ]

        return tasks, len(tasks)
