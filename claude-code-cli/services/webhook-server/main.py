"""Webhook Server - FastAPI application with plugin-based architecture."""

import sys
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from config import settings
from metrics import metrics

# Import webhook registry and plugin system
from core.webhook_registry import webhook_registry
from core.webhook_base import WebhookResponse

# Import dashboard API routes
from routes import dashboard_api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Agent Webhook Server",
    description="Webhook receiver for AI Agent System (Plugin-Based Architecture)",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include dashboard API router
app.include_router(dashboard_api.router)

# Auto-discover and register all webhook handlers on startup
@app.on_event("startup")
async def startup_event():
    """Initialize webhook registry on startup."""
    logger.info("=" * 60)
    logger.info("Webhook Server Starting Up")
    logger.info("=" * 60)

    # Auto-discover webhooks
    webhook_registry.auto_discover()

    # Log registered webhooks
    handlers = webhook_registry.list_handlers()
    stats = webhook_registry.get_stats()
    logger.info(f"Webhook Registry Stats: {stats}")
    logger.info(f"Registered {len(handlers)} webhook handlers:")
    for handler in handlers:
        logger.info(f"  ✓ {handler.name}: {handler.endpoint} - {handler.description}")

    logger.info("=" * 60)
    logger.info("Webhook Server Ready")
    logger.info("=" * 60)


# Generic webhook handler endpoint
async def generic_webhook_handler(
    webhook_name: str,
    request: Request,
    x_hub_signature: str = Header(None, alias="X-Hub-Signature"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_slack_signature: str = Header(None, alias="X-Slack-Signature"),
):
    """
    Generic webhook handler that routes to registered handlers.

    Args:
        webhook_name: Name of webhook handler to use
        request: FastAPI request
        x_hub_signature: GitHub signature (SHA-1)
        x_hub_signature_256: GitHub signature (SHA-256)
        x_slack_signature: Slack signature

    Returns:
        WebhookResponse dict
    """
    handler = webhook_registry.get_handler(webhook_name)
    if not handler:
        raise HTTPException(status_code=404, detail=f"Webhook handler '{webhook_name}' not found")

    try:
        # Get raw payload for signature validation
        raw_payload = await request.body()

        # Determine signature header (try all common headers)
        signature = x_hub_signature_256 or x_hub_signature or x_slack_signature or ""

        # Validate signature if provided
        if signature:
            is_valid = await handler.validate_signature(raw_payload, signature)
            if not is_valid:
                logger.warning(f"Invalid signature for {webhook_name} webhook")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        # Parse JSON payload
        payload = await request.json()
        parsed_data = await handler.parse_payload(payload)

        if parsed_data is None:
            return WebhookResponse(
                status="error",
                message="Failed to parse webhook payload"
            ).model_dump()

        # Check if should process
        should_process = await handler.should_process(parsed_data)

        if not should_process:
            return WebhookResponse(
                status="ignored",
                message="Event does not meet processing criteria"
            ).model_dump()

        # Handle webhook
        result = await handler.handle(parsed_data)

        # Return result
        response = result.model_dump()
        logger.info(f"{webhook_name} webhook processed: {response.get('status')}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing {webhook_name} webhook: {e}")
        error_response = await handler.on_error(e)
        return error_response.model_dump()


# Register webhook endpoints
@app.post("/webhooks/jira", tags=["Webhooks"])
async def jira_webhook(request: Request, x_hub_signature_256: str = Header(None)):
    """Jira webhook endpoint."""
    return await generic_webhook_handler("jira", request, x_hub_signature_256=x_hub_signature_256)


@app.post("/webhooks/github", tags=["Webhooks"])
async def github_webhook(request: Request, x_hub_signature_256: str = Header(None)):
    """GitHub webhook endpoint."""
    return await generic_webhook_handler("github", request, x_hub_signature_256=x_hub_signature_256)


@app.post("/webhooks/sentry", tags=["Webhooks"])
async def sentry_webhook(request: Request):
    """Sentry webhook endpoint."""
    return await generic_webhook_handler("sentry", request)


@app.post("/webhooks/slack", tags=["Webhooks"])
async def slack_webhook(request: Request, x_slack_signature: str = Header(None)):
    """Slack webhook endpoint."""
    return await generic_webhook_handler("slack", request, x_slack_signature=x_slack_signature)


@app.get("/")
async def root():
    """Root endpoint."""
    handlers = webhook_registry.list_handlers()
    stats = webhook_registry.get_stats()

    return {
        "service": "AI Agent Webhook Server",
        "version": "2.0.0",
        "status": "running",
        "architecture": "plugin-based",
        "webhooks": {
            "registered": [
                {
                    "name": h.name,
                    "endpoint": h.endpoint,
                    "description": h.description,
                    "enabled": h.enabled
                }
                for h in handlers
            ],
            "stats": stats
        }
    }


@app.get("/webhooks", tags=["Webhooks"])
async def list_webhooks():
    """List all registered webhook handlers."""
    handlers = webhook_registry.list_handlers()
    stats = webhook_registry.get_stats()

    return {
        "webhooks": [
            {
                "name": h.name,
                "endpoint": h.endpoint,
                "description": h.description,
                "enabled": h.enabled,
                "secret_env_var": h.secret_env_var
            }
            for h in handlers
        ],
        "stats": stats
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
