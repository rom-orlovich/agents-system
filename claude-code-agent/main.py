"""Main entry point for Claude Code Agent."""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import structlog
from sqlalchemy import update

from core import (
    settings,
    setup_logging,
    WebSocketHub,
)
from core.database import init_db, async_session_factory
from core.database.redis_client import redis_client
from core.database.models import SessionDB
from api import credentials, dashboard, registry, analytics, websocket, conversations
from api import webhooks_dynamic, webhook_status
from api import subagents, container, accounts, sessions
from api.webhooks import router as webhooks_router
from core.webhook_configs import validate_webhook_configs
from workers.task_worker import TaskWorker
from shared.machine_models import ClaudeCredentials

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

    # Validate webhook configurations
    validate_webhook_configs()

    # Check credentials (CLI test only runs after credentials upload, not on startup)
    creds_path = settings.credentials_path
    if creds_path.exists():
        try:
            # Load credentials to get user_id for logging
            creds_data = json.loads(creds_path.read_text())
            creds = ClaudeCredentials.from_dict(creds_data)
            user_id = creds.user_id or creds.account_id
            
            if user_id:
                logger.info("Credentials found", user_id=user_id)
            else:
                logger.warning("No user_id found in credentials")
        except Exception as e:
            # Don't fail startup - just log error
            logger.warning("Failed to load credentials during startup", error=str(e))
    else:
        # Credentials don't exist - this is OK, just log info
        logger.info("Credentials file not found - app will start normally. Upload credentials via dashboard.")

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

# Include routers
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(credentials.router, prefix="/api", tags=["credentials"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(registry.router, prefix="/api", tags=["registry"])
app.include_router(webhook_status.router, prefix="/api", tags=["webhooks"])
app.include_router(webhooks_router, tags=["webhooks"])  # Static webhooks (hard-coded)
app.include_router(webhooks_dynamic.router, prefix="/webhooks", tags=["webhooks-dynamic"])  # Dynamic webhooks (database-driven)
app.include_router(websocket.router, tags=["websocket"])

# V2 API routers (Multi-Subagent Orchestration)
app.include_router(subagents.router, tags=["subagents"])
app.include_router(container.router, tags=["container"])
app.include_router(accounts.router, tags=["accounts", "machines"])
app.include_router(sessions.router, tags=["sessions"])

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
    try:
        queue_length = await redis_client.queue_length()
    except Exception:
        # Graceful degradation if Redis is down
        queue_length = -1

    return {
        "status": "healthy",
        "machine_id": settings.machine_id,
        "queue_length": queue_length,
        "sessions": ws_hub.get_session_count(),
        "connections": ws_hub.get_connection_count(),
    }


# Make ws_hub available to routers
app.state.ws_hub = ws_hub
