"""Analytics endpoints."""

from typing import Any
from fastapi import APIRouter
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.get("/summary")
async def get_summary() -> dict[str, Any]:
    """Get analytics summary."""
    return {
        "total_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "avg_duration_seconds": 0.0,
    }


@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """Get detailed metrics."""
    return {
        "tasks_by_status": {},
        "tasks_by_type": {},
        "hourly_distribution": {},
    }
