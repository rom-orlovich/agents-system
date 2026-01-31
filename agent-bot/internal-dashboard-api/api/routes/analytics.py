from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from services import TaskManager

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
task_manager = TaskManager()


class AnalyticsSummary(BaseModel):
    today_cost: float
    today_tasks: int
    total_cost: float
    total_tasks: int
    success_rate: float
    average_duration_seconds: float


class TasksByStatus(BaseModel):
    status: str
    count: int


class TasksBySource(BaseModel):
    source: str
    count: int


class TasksOverTime(BaseModel):
    date: str
    completed: int
    failed: int


class AnalyticsResponse(BaseModel):
    tasks_by_status: list[TasksByStatus]
    tasks_by_source: list[TasksBySource]
    tasks_over_time: list[TasksOverTime]
    average_duration_seconds: float
    total_cost_usd: float
    success_rate: float


@router.get("/summary")
async def get_analytics_summary() -> AnalyticsSummary:
    stats = await task_manager.get_task_stats()

    completed = stats.get("completed", 0)
    failed = stats.get("failed", 0)
    total = completed + failed + stats.get("pending", 0) + stats.get("running", 0)

    success_rate = (completed / total * 100) if total > 0 else 0.0

    return AnalyticsSummary(
        today_cost=stats.get("today_cost", 0.0),
        today_tasks=stats.get("today_tasks", 0),
        total_cost=stats.get("total_cost", 0.0),
        total_tasks=total,
        success_rate=success_rate,
        average_duration_seconds=stats.get("average_duration", 0.0),
    )


@router.get("")
async def get_analytics(
    period: Annotated[str, Query(pattern="^(day|week|month)$")] = "week",
) -> AnalyticsResponse:
    now = datetime.now(timezone.utc)

    if period == "day":
        start_date = now - timedelta(days=1)
        days = 1
    elif period == "week":
        start_date = now - timedelta(days=7)
        days = 7
    else:
        start_date = now - timedelta(days=30)
        days = 30

    stats = await task_manager.get_task_stats()

    tasks_by_status = [
        TasksByStatus(status="completed", count=stats.get("completed", 0)),
        TasksByStatus(status="failed", count=stats.get("failed", 0)),
        TasksByStatus(status="pending", count=stats.get("pending", 0)),
        TasksByStatus(status="running", count=stats.get("running", 0)),
    ]

    tasks_by_source = [
        TasksBySource(source="github", count=stats.get("github_tasks", 0)),
        TasksBySource(source="jira", count=stats.get("jira_tasks", 0)),
        TasksBySource(source="slack", count=stats.get("slack_tasks", 0)),
        TasksBySource(source="sentry", count=stats.get("sentry_tasks", 0)),
        TasksBySource(source="internal", count=stats.get("internal_tasks", 0)),
    ]

    tasks_over_time = []
    for i in range(days):
        date = (now - timedelta(days=days - i - 1)).strftime("%Y-%m-%d")
        tasks_over_time.append(TasksOverTime(
            date=date,
            completed=stats.get(f"completed_{date}", 0),
            failed=stats.get(f"failed_{date}", 0),
        ))

    completed = stats.get("completed", 0)
    failed = stats.get("failed", 0)
    total = completed + failed
    success_rate = (completed / total * 100) if total > 0 else 0.0

    return AnalyticsResponse(
        tasks_by_status=tasks_by_status,
        tasks_by_source=tasks_by_source,
        tasks_over_time=tasks_over_time,
        average_duration_seconds=stats.get("average_duration", 0.0),
        total_cost_usd=stats.get("total_cost", 0.0),
        success_rate=success_rate,
    )


@router.get("/costs/histogram")
async def get_costs_histogram(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    granularity: Annotated[str, Query(pattern="^(day|hour)$")] = "day",
):
    stats = await task_manager.get_task_stats()

    dates = []
    costs = []
    task_counts = []

    now = datetime.now(timezone.utc)
    for i in range(days):
        date = (now - timedelta(days=days - i - 1)).strftime("%Y-%m-%d")
        dates.append(date)
        costs.append(stats.get(f"cost_{date}", 0.0))
        task_counts.append(stats.get(f"tasks_{date}", 0))

    return {
        "dates": dates,
        "costs": costs,
        "task_counts": task_counts,
        "tokens": [0] * len(dates),
        "avg_latency": [0.0] * len(dates),
        "error_counts": [0] * len(dates),
    }


@router.get("/costs/by-subagent")
async def get_costs_by_subagent(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
):
    return {
        "subagents": ["brain", "planning", "executor", "verifier"],
        "costs": [0.0, 0.0, 0.0, 0.0],
        "task_counts": [0, 0, 0, 0],
    }
