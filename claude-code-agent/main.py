"""Main entry point for Claude Code Agent."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import structlog

from core import (
    settings,
    setup_logging,
    WebSocketHub,
    AgentError,
    AuthenticationError,
    TaskError,
    agent_error_handler,
    auth_error_handler,
    task_error_handler,
)
from core.database import init_db
from core.database.redis_client import redis_client
from api import dashboard, websocket, webhooks
from workers.task_worker import TaskWorker

# Setup logging
setup_logging()
logger = structlog.get_logger()

# Global WebSocket hub
ws_hub = WebSocketHub()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    logger.info("Starting Claude Code Agent", machine_id=settings.machine_id)

    # Initialize database
    await init_db()

    # Connect to Redis
    await redis_client.connect()

    # Start task worker
    worker = TaskWorker(ws_hub)
    worker_task = asyncio.create_task(worker.run())

    logger.info(
        "Claude Code Agent ready",
        machine_id=settings.machine_id,
        port=settings.api_port
    )

    yield

    # Shutdown
    logger.info("Shutting down Claude Code Agent")
    await worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await redis_client.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Claude Code Agent",
    description="Claude Code CLI Agent with dashboard and webhook support",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AgentError, agent_error_handler)
app.add_exception_handler(AuthenticationError, auth_error_handler)
app.add_exception_handler(TaskError, task_error_handler)

# Include routers
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

# Serve static files (dashboard frontend)
try:
    app.mount("/static", StaticFiles(directory="services/dashboard/static"), name="static")
except RuntimeError:
    logger.warning("Static files directory not found, skipping mount")


@app.get("/")
async def root():
    """Redirect to dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    queue_length = await redis_client.queue_length()
    return {
        "status": "healthy",
        "machine_id": settings.machine_id,
        "queue_length": queue_length,
        "sessions": ws_hub.get_session_count(),
        "connections": ws_hub.get_connection_count(),
    }


# Make ws_hub available to routers
app.state.ws_hub = ws_hub
