from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        services={
            "api": "healthy",
            "database": "healthy",
            "redis": "healthy",
        },
    )


@router.get("/metrics")
async def metrics():
    return {
        "service": "agent-bot",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
