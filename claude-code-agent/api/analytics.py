"""Analytics API endpoints."""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database import get_session as get_db_session
from core.database.models import TaskDB
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/analytics", tags=["analytics"])


class AnalyticsSummary(BaseModel):
    """Analytics summary response."""
    today_cost: float
    today_tasks: int
    total_cost: float
    total_tasks: int


class DailyCostsResponse(BaseModel):
    """Daily costs response for Chart.js."""
    dates: List[str]
    costs: List[float]
    task_counts: List[int]
    tokens: List[int]
    avg_latency: List[float]
    error_counts: List[int]


class SubagentCostsResponse(BaseModel):
    """Subagent costs response for Chart.js."""
    subagents: List[str]
    costs: List[float]
    task_counts: List[int]


@router.get("/summary")
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db_session)
) -> AnalyticsSummary:
    """Get overall analytics summary."""
    today = datetime.utcnow().date()
    
    # Today's stats
    today_q = select(
        func.sum(TaskDB.cost_usd),
        func.count(TaskDB.task_id)
    ).where(
        func.date(TaskDB.created_at) == today
    )
    today_r = (await db.execute(today_q)).one()
    
    # All time stats
    all_q = select(
        func.sum(TaskDB.cost_usd),
        func.count(TaskDB.task_id)
    )
    all_r = (await db.execute(all_q)).one()
    
    return AnalyticsSummary(
        today_cost=float(today_r[0] or 0),
        today_tasks=int(today_r[1] or 0),
        total_cost=float(all_r[0] or 0),
        total_tasks=int(all_r[1] or 0),
    )


@router.get("/costs/histogram")
async def get_costs_histogram(
    days: int = Query(30, ge=1, le=365),
    granularity: str = Query("day", regex="^(day|hour)$"),
    db: AsyncSession = Depends(get_db_session)
) -> DailyCostsResponse:
    """Get cost aggregation with variable granularity."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Granularity logic
    if granularity == "hour":
        # SQLite format for hourly: YYYY-MM-DD HH:00:00
        time_group = func.strftime('%Y-%m-%d %H:00:00', TaskDB.created_at)
        date_label = time_group
    else:
        # SQLite format for daily: YYYY-MM-DD
        time_group = func.date(TaskDB.created_at)
        date_label = time_group

    # We use case to count non-null errors
    error_case = func.sum(func.case((TaskDB.error != None, 1), else_=0))

    query = select(
        time_group.label("date"),
        func.sum(TaskDB.cost_usd).label("total_cost"),
        func.count(TaskDB.task_id).label("task_count"),
        func.sum(TaskDB.input_tokens + TaskDB.output_tokens).label("total_tokens"),
        func.avg(TaskDB.duration_seconds).label("avg_duration"),
        error_case.label("error_count")
    ).where(
        TaskDB.created_at >= start_date
    ).group_by(
        time_group
    ).order_by(
        time_group.asc()
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    return DailyCostsResponse(
        dates=[str(r.date) for r in rows],
        costs=[float(r.total_cost or 0) for r in rows],
        task_counts=[int(r.task_count) for r in rows],
        tokens=[int(r.total_tokens or 0) for r in rows],
        avg_latency=[float(r.avg_duration or 0) * 1000 for r in rows], # Convert to ms
        error_counts=[int(r.error_count or 0) for r in rows],
    )


@router.get("/costs/by-subagent")
async def get_costs_by_subagent(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db_session)
) -> SubagentCostsResponse:
    """Get cost breakdown by subagent."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(
        TaskDB.assigned_agent,
        func.sum(TaskDB.cost_usd).label("total_cost"),
        func.count(TaskDB.task_id).label("task_count"),
    ).where(
        TaskDB.created_at >= start_date
    ).group_by(
        TaskDB.assigned_agent
    ).order_by(
        func.sum(TaskDB.cost_usd).desc()
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    return SubagentCostsResponse(
        subagents=[r.assigned_agent or "unknown" for r in rows],
        costs=[float(r.total_cost or 0) for r in rows],
        task_counts=[int(r.task_count) for r in rows],
    )
