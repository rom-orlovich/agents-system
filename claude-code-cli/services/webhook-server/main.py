"""Webhook Server - FastAPI application."""

import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import settings
from shared.metrics import metrics

# Import routes
from routes import jira, sentry, github, slack

app = FastAPI(
    title="AI Agent Webhook Server",
    description="Webhook receiver for AI Agent System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(jira.router, prefix="/webhooks/jira", tags=["Jira"])
app.include_router(sentry.router, prefix="/webhooks/sentry", tags=["Sentry"])
app.include_router(github.router, prefix="/webhooks/github", tags=["GitHub"])
app.include_router(slack.router, prefix="/webhooks/slack", tags=["Slack"])


@app.on_event("startup")
async def startup_event():
    print("Registered routes:")
    for route in app.routes:
        print(f"  {route.path} [{route.methods}]")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AI Agent Webhook Server",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "webhook-server"
    }


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(metrics.get_metrics())


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    print(f"Error processing request: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
