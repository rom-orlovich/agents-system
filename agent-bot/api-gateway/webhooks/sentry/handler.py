import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import structlog

from config import get_settings
from .events import should_process_event, extract_task_info

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/webhooks/sentry", tags=["sentry-webhook"])


@router.post("")
async def handle_sentry_webhook(
    request: Request,
    sentry_hook_resource: Annotated[str | None, Header()] = None,
):
    payload = await request.body()
    data = json.loads(payload)
    action = data.get("action", "")

    logger.info(
        "sentry_webhook_received",
        action=action,
        resource=sentry_hook_resource,
    )

    if not should_process_event(action, data):
        logger.debug("sentry_event_skipped", action=action)
        return JSONResponse(
            status_code=200,
            content={"status": "skipped", "reason": "Event not processed"},
        )

    task_info = extract_task_info(action, data)
    task_id = str(uuid.uuid4())
    task_info["task_id"] = task_id

    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url)
    await redis_client.lpush("agent:tasks", json.dumps(task_info))
    await redis_client.aclose()

    logger.info(
        "sentry_task_queued",
        task_id=task_id,
        issue_id=task_info.get("issue", {}).get("id"),
    )

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "task_id": task_id},
    )


@router.get("/health")
async def health_check():
    return {"status": "healthy", "webhook": "sentry"}
