import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import structlog

from config import get_settings
from .events import should_process_event, extract_task_info

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/webhooks/jira", tags=["jira-webhook"])


@router.post("")
async def handle_jira_webhook(request: Request):
    payload = await request.body()
    data = json.loads(payload)
    webhook_event = data.get("webhookEvent", "")
    issue = data.get("issue", {})

    logger.info(
        "jira_webhook_received",
        event_type=webhook_event,
        issue_key=issue.get("key"),
    )

    if not should_process_event(webhook_event, issue):
        logger.debug(
            "jira_event_skipped",
            event_type=webhook_event,
            reason="Missing AI-Fix label or unsupported event",
        )
        return JSONResponse(
            status_code=200,
            content={"status": "skipped", "reason": "Event not processed"},
        )

    task_info = extract_task_info(webhook_event, data)
    task_id = str(uuid.uuid4())
    task_info["task_id"] = task_id

    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url)
    await redis_client.lpush("agent:tasks", json.dumps(task_info))
    await redis_client.aclose()

    logger.info("jira_task_queued", task_id=task_id, issue_key=issue.get("key"))

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "task_id": task_id},
    )


@router.get("/health")
async def health_check():
    return {"status": "healthy", "webhook": "jira"}
