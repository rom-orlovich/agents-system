from fastapi import APIRouter, HTTPException, Query
from api.models import (
    TaskLogsResponse,
    TaskLogEntry,
    AnalyticsResponse,
    AnalyticsMetrics,
    ServiceMetrics,
    TaskListResponse,
    TaskListItem,
)
from storage.log_reader import LogReader
from storage.analytics_repository import AnalyticsRepository
from datetime import datetime, timedelta, timezone
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

log_reader = LogReader()
analytics_repo = AnalyticsRepository()


@router.get("/tasks/{task_id}/logs", response_model=TaskLogsResponse)
async def get_task_logs(task_id: str):
    try:
        logs = await log_reader.read_task_logs(task_id)
        return logs
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    except Exception as e:
        logger.error("get_task_logs_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    period_days: int = Query(default=7, ge=1, le=90),
):
    try:
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(days=period_days)

        overall_metrics = await analytics_repo.get_overall_metrics(
            period_start, period_end
        )
        service_metrics = await analytics_repo.get_service_metrics(
            period_start, period_end
        )

        return AnalyticsResponse(
            period_start=period_start,
            period_end=period_end,
            overall_metrics=overall_metrics,
            service_metrics=service_metrics,
        )
    except Exception as e:
        logger.error("get_analytics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    user_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
):
    try:
        tasks, total = await analytics_repo.list_tasks(
            user_id=user_id,
            status=status,
            page=page,
            page_size=page_size,
        )

        return TaskListResponse(
            tasks=tasks,
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error("list_tasks_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
