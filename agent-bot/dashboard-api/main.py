from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import (
    analytics,
    conversations,
    dashboard,
    oauth_status,
    sources,
    webhook_status,
    websocket,
)
from core.config import Settings
from core.database import init_db, shutdown_db

logger = structlog.get_logger()

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("dashboard_starting")
    await init_db()
    logger.info("dashboard_started")
    yield
    logger.info("dashboard_shutting_down")
    await shutdown_db()
    logger.info("dashboard_stopped")


app = FastAPI(
    title="Agent Bot Dashboard",
    version="1.0.0",
    description="Enhanced dashboard with task streaming and analytics",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(webhook_status.router, prefix="/api", tags=["webhooks"])
app.include_router(oauth_status.router, prefix="/api", tags=["oauth"])
app.include_router(sources.router, tags=["sources"])
app.include_router(websocket.router, tags=["websocket"])


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "dashboard-api"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
