"""Session status and management API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_session
from core.database.redis_client import redis_client
from core.database.models import SessionDB, TaskDB

router = APIRouter(prefix="/api/v2", tags=["sessions"])


class SessionStatus(BaseModel):
    """Session status information."""
    session_id: str
    status: str  # active, idle, disconnected
    running_tasks: int
    total_cost_usd: float
    total_tasks: int
    started_at: Optional[str] = None
    last_activity: Optional[str] = None
    duration_seconds: int = 0


# ==================== Session Status ====================

@router.get("/sessions/{session_id}", response_model=dict)
async def get_session_details(
    session_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Get session details."""
    result = await db.execute(
        select(SessionDB).where(SessionDB.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # Get running tasks from Redis
    running_tasks = await redis_client.get_session_tasks(session_id)
    
    # Calculate duration
    duration = 0
    if session.connected_at:
        end_time = session.disconnected_at or datetime.now(timezone.utc)
        # SQLite returns naive datetimes, convert to UTC-aware for comparison
        connected_at = session.connected_at
        if connected_at.tzinfo is None:
            connected_at = connected_at.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        duration = int((end_time - connected_at).total_seconds())
    
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "machine_id": session.machine_id,
        "status": "active" if running_tasks else ("disconnected" if session.disconnected_at else "idle"),
        "running_tasks": len(running_tasks),
        "total_cost_usd": session.total_cost_usd,
        "total_tasks": session.total_tasks,
        "connected_at": session.connected_at.isoformat() if session.connected_at else None,
        "disconnected_at": session.disconnected_at.isoformat() if session.disconnected_at else None,
        "duration_seconds": duration
    }


@router.get("/sessions/{session_id}/status", response_model=dict)
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Get session status."""
    result = await db.execute(
        select(SessionDB).where(SessionDB.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # Get running tasks
    running_tasks = await redis_client.get_session_tasks(session_id)
    
    # Determine status
    if session.disconnected_at:
        status_str = "disconnected"
    elif running_tasks:
        status_str = "active"
    else:
        status_str = "idle"
    
    return {
        "session_id": session_id,
        "status": status_str,
        "running_tasks": len(running_tasks)
    }


@router.post("/sessions/{session_id}/reset", response_model=dict)
async def reset_session(
    session_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Reset session context while preserving history."""
    result = await db.execute(
        select(SessionDB).where(SessionDB.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # Get conversations for this session's user
    # Note: In a full implementation, we'd track session-conversation relationship
    # For now, we preserve cost but could clear context
    
    reset_at = datetime.now(timezone.utc)
    
    return {
        "success": True,
        "session_id": session_id,
        "reset_at": reset_at.isoformat(),
        "cost_preserved": session.total_cost_usd
    }


@router.get("/sessions/summary/weekly", response_model=dict)
async def get_weekly_summary(db: AsyncSession = Depends(get_session)):
    """Get weekly session summary."""
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Get sessions from last 7 days
    result = await db.execute(
        select(SessionDB).where(SessionDB.connected_at >= week_ago)
    )
    sessions = result.scalars().all()
    
    # Get tasks from last 7 days
    tasks_result = await db.execute(
        select(TaskDB).where(TaskDB.created_at >= week_ago)
    )
    tasks = tasks_result.scalars().all()
    
    # Calculate totals
    total_cost = sum(s.total_cost_usd for s in sessions)
    total_tasks = len(tasks)
    
    # Calculate active days
    active_dates = set()
    for s in sessions:
        if s.connected_at:
            active_dates.add(s.connected_at.date())
    
    # Build daily breakdown
    daily = []
    for i in range(7):
        date = (datetime.now(timezone.utc) - timedelta(days=i)).date()
        # SQLite returns naive datetimes, handle both naive and aware
        day_sessions = [
            s for s in sessions 
            if s.connected_at and (
                s.connected_at.date() == date if s.connected_at.tzinfo is None
                else s.connected_at.replace(tzinfo=None).date() == date
            )
        ]
        day_tasks = [
            t for t in tasks 
            if t.created_at and (
                t.created_at.date() == date if t.created_at.tzinfo is None
                else t.created_at.replace(tzinfo=None).date() == date
            )
        ]
        
        daily.append({
            "date": date.isoformat(),
            "sessions": len(day_sessions),
            "task_count": len(day_tasks),
            "cost_usd": sum(s.total_cost_usd for s in day_sessions)
        })
    
    return {
        "total_cost_usd": total_cost,
        "total_tasks": total_tasks,
        "active_days": len(active_dates),
        "sessions": len(sessions),
        "daily": daily
    }


# ==================== Dashboard Endpoints ====================

@router.get("/dashboard/session/current", response_model=dict)
async def get_current_session(db: AsyncSession = Depends(get_session)):
    """Get current session for dashboard display."""
    # Get most recent active session
    result = await db.execute(
        select(SessionDB)
        .where(SessionDB.disconnected_at.is_(None))
        .order_by(SessionDB.connected_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        # Return empty state
        return {
            "session_id": None,
            "status": "disconnected",
            "running_tasks": 0,
            "total_cost_usd": 0.0,
            "total_tasks": 0,
            "started_at": None,
            "duration_seconds": 0
        }
    
    # Get running tasks
    running_tasks = await redis_client.get_session_tasks(session.session_id)
    
    # Calculate duration
    duration = 0
    if session.connected_at:
        # SQLite returns naive datetimes, convert to UTC-aware for comparison
        connected_at = session.connected_at
        if connected_at.tzinfo is None:
            connected_at = connected_at.replace(tzinfo=timezone.utc)
        duration = int((datetime.now(timezone.utc) - connected_at).total_seconds())
    
    return {
        "session_id": session.session_id,
        "status": "active" if running_tasks else "idle",
        "running_tasks": len(running_tasks),
        "total_cost_usd": session.total_cost_usd,
        "total_tasks": session.total_tasks,
        "started_at": session.connected_at.isoformat() if session.connected_at else None,
        "last_activity": None,  # Would need to track this
        "duration_seconds": duration
    }


@router.get("/dashboard/sessions/history", response_model=dict)
async def get_session_history(
    days: int = 7,
    db: AsyncSession = Depends(get_session)
):
    """Get session history for dashboard."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await db.execute(
        select(SessionDB)
        .where(SessionDB.connected_at >= cutoff)
        .order_by(SessionDB.connected_at.desc())
    )
    sessions = result.scalars().all()
    
    # Group by day
    daily = {}
    for session in sessions:
        if session.connected_at:
            date_str = session.connected_at.date().isoformat()
            if date_str not in daily:
                daily[date_str] = {
                    "date": date_str,
                    "sessions": 0,
                    "total_cost": 0.0,
                    "task_count": 0
                }
            daily[date_str]["sessions"] += 1
            daily[date_str]["total_cost"] += session.total_cost_usd
            daily[date_str]["task_count"] += session.total_tasks
    
    return {
        "days": days,
        "daily": list(daily.values()),
        "total_sessions": len(sessions)
    }
