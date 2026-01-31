"""Analytics API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database import get_session as get_db_session
from core.database.models import TaskDB, ConversationDB
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
    db: AsyncSession = Depends(get_db_session),
) -> AnalyticsSummary:
    """Get overall analytics summary."""
    # Use datetime range for SQLite compatibility instead of func.date()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Today's stats
    today_q = select(func.sum(TaskDB.cost_usd), func.count(TaskDB.task_id)).where(
        TaskDB.created_at >= today_start
    )
    today_r = (await db.execute(today_q)).one()

    # All time stats
    all_q = select(func.sum(TaskDB.cost_usd), func.count(TaskDB.task_id))
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
    granularity: str = Query("day", pattern="^(day|hour)$"),
    db: AsyncSession = Depends(get_db_session),
) -> DailyCostsResponse:
    """Get cost aggregation with variable granularity."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Detect database dialect
    try:
        bind = (
            db.get_bind()
            if hasattr(db, "get_bind")
            else (db.bind if hasattr(db, "bind") else None)
        )
        dialect_name = bind.dialect.name if bind else None
    except Exception:
        dialect_name = None
    is_sqlite = dialect_name == "sqlite"

    # Granularity logic - use appropriate function based on database
    if granularity == "hour":
        if is_sqlite:
            time_group = func.strftime("%Y-%m-%d %H:00:00", TaskDB.created_at)
        else:
            # PostgreSQL
            time_group = func.to_char(TaskDB.created_at, "YYYY-MM-DD HH24:00:00")
    else:
        # Daily granularity
        if is_sqlite:
            time_group = func.strftime("%Y-%m-%d", TaskDB.created_at)
        else:
            # PostgreSQL
            time_group = func.to_char(TaskDB.created_at, "YYYY-MM-DD")

    # We use case to count non-null errors
    error_case = func.sum(case((TaskDB.error.isnot(None), 1), else_=0))

    query = (
        select(
            time_group.label("date"),
            func.sum(TaskDB.cost_usd).label("total_cost"),
            func.count(TaskDB.task_id).label("task_count"),
            func.sum(TaskDB.input_tokens + TaskDB.output_tokens).label("total_tokens"),
            func.avg(TaskDB.duration_seconds).label("avg_duration"),
            error_case.label("error_count"),
        )
        .where(TaskDB.created_at >= start_date)
        .group_by(time_group)
        .order_by(time_group.asc())
    )

    result = await db.execute(query)
    rows = result.all()

    return DailyCostsResponse(
        dates=[str(r.date) for r in rows],
        costs=[float(r.total_cost or 0) for r in rows],
        task_counts=[int(r.task_count) for r in rows],
        tokens=[int(r.total_tokens or 0) for r in rows],
        avg_latency=[float(r.avg_duration or 0) * 1000 for r in rows],  # Convert to ms
        error_counts=[int(r.error_count or 0) for r in rows],
    )


@router.get("/costs/by-subagent")
async def get_costs_by_subagent(
    days: int = Query(30, ge=1, le=365), db: AsyncSession = Depends(get_db_session)
) -> SubagentCostsResponse:
    """Get cost breakdown by subagent."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            TaskDB.assigned_agent,
            func.sum(TaskDB.cost_usd).label("total_cost"),
            func.count(TaskDB.task_id).label("task_count"),
        )
        .where(TaskDB.created_at >= start_date)
        .group_by(TaskDB.assigned_agent)
        .order_by(func.sum(TaskDB.cost_usd).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    # Filter out NULL assigned_agent values and return empty if no valid rows
    valid_rows = [r for r in rows if r.assigned_agent is not None]
    if not valid_rows:
        return SubagentCostsResponse(
            subagents=[],
            costs=[],
            task_counts=[],
        )

    return SubagentCostsResponse(
        subagents=[r.assigned_agent for r in valid_rows],
        costs=[float(r.total_cost or 0) for r in valid_rows],
        task_counts=[int(r.task_count) for r in valid_rows],
    )


@router.get("/conversations")
async def get_conversations_analytics(
    start_date: str = Query(None, description="Start date (ISO format)"),
    end_date: str = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db_session),
):
    """Get conversation-level analytics aggregated across all conversations."""
    query = select(ConversationDB)

    # Apply date filters if provided
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.where(ConversationDB.started_at >= start_dt)
        except ValueError:
            logger.warning("invalid_start_date", start_date=start_date)

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.where(ConversationDB.started_at <= end_dt)
        except ValueError:
            logger.warning("invalid_end_date", end_date=end_date)

    result = await db.execute(query)
    conversations = result.scalars().all()

    # Aggregate metrics
    total_conversations = len(conversations)
    total_cost_usd = sum(conv.total_cost_usd or 0.0 for conv in conversations)
    total_tasks = sum(conv.total_tasks or 0 for conv in conversations)
    total_duration_seconds = sum(
        conv.total_duration_seconds or 0.0 for conv in conversations
    )

    # Calculate averages
    avg_cost_per_conversation = (
        total_cost_usd / total_conversations if total_conversations > 0 else 0.0
    )
    avg_tasks_per_conversation = (
        total_tasks / total_conversations if total_conversations > 0 else 0.0
    )

    return {
        "total_conversations": total_conversations,
        "total_cost_usd": round(total_cost_usd, 4),
        "total_tasks": total_tasks,
        "total_duration_seconds": round(total_duration_seconds, 2),
        "avg_cost_per_conversation": round(avg_cost_per_conversation, 4),
        "avg_tasks_per_conversation": round(avg_tasks_per_conversation, 2),
        "conversations": [
            {
                "conversation_id": conv.conversation_id,
                "title": conv.title,
                "total_cost_usd": conv.total_cost_usd or 0.0,
                "total_tasks": conv.total_tasks or 0,
                "total_duration_seconds": conv.total_duration_seconds or 0.0,
                "started_at": conv.started_at.isoformat() if conv.started_at else None,
                "completed_at": conv.completed_at.isoformat()
                if conv.completed_at
                else None,
            }
            for conv in conversations
        ],
    }
