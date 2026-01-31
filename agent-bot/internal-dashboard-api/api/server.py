from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import agents_router, tasks_router, monitoring_router, metrics_router
from middleware import AuthMiddleware, error_handler

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("internal_dashboard_api_starting")
    yield
    logger.info("internal_dashboard_api_shutting_down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Internal Dashboard API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuthMiddleware)
    app.add_exception_handler(Exception, error_handler)

    app.include_router(agents_router)
    app.include_router(tasks_router)
    app.include_router(monitoring_router)
    app.include_router(metrics_router)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "internal-dashboard-api"}

    @app.get("/")
    async def root():
        return {
            "service": "internal-dashboard-api",
            "version": "1.0.0",
            "endpoints": {
                "agents": "/api/v1/agents",
                "tasks": "/api/v1/tasks",
                "monitoring": "/api/v1/monitoring",
                "metrics": "/api/v1/metrics",
            },
        }

    return app
