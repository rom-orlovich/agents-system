from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import structlog
import os
from queue.redis_queue import TaskQueue
from webhooks.receiver import WebhookReceiver
from core.models import WebhookResponse

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
task_queue = TaskQueue(redis_url=redis_url)
webhook_receiver = WebhookReceiver(task_queue=task_queue)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await task_queue.connect()
    logger.info("api_gateway_started", redis_url=redis_url)
    yield
    await task_queue.disconnect()
    logger.info("api_gateway_stopped")


app = FastAPI(
    title="API Gateway",
    description="Webhook receiver and task queue management",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    queue_length = await task_queue.get_queue_length()
    return {
        "status": "healthy",
        "service": "api-gateway",
        "queue_length": queue_length,
    }


@app.post("/webhooks/github", response_model=WebhookResponse)
async def receive_github_webhook(request: Request):
    return await webhook_receiver.receive_github_webhook(request)


@app.post("/webhooks/jira", response_model=WebhookResponse)
async def receive_jira_webhook(request: Request):
    return await webhook_receiver.receive_jira_webhook(request)


@app.post("/webhooks/slack", response_model=WebhookResponse)
async def receive_slack_webhook(request: Request):
    return await webhook_receiver.receive_slack_webhook(request)


@app.post("/webhooks/sentry", response_model=WebhookResponse)
async def receive_sentry_webhook(request: Request):
    return await webhook_receiver.receive_sentry_webhook(request)
