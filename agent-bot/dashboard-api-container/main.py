"""Dashboard API entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog

from api.routes import analytics, logs, tasks

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

app = FastAPI(
    title="Dashboard API",
    version="0.1.0",
    description="Analytics and monitoring API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "dashboard-api"}
