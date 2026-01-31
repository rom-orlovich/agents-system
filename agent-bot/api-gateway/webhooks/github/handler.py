import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import structlog

from config import get_settings
from .validator import validate_github_signature
from .events import should_process_event, extract_task_info

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/webhooks/github", tags=["github-webhook"])


@router.post("")
async def handle_github_webhook(
    request: Request,
    x_github_event: Annotated[str, Header()],
    x_hub_signature_256: Annotated[str | None, Header()] = None,
):
    payload = await request.body()
    validate_github_signature(payload, x_hub_signature_256)

    data = json.loads(payload)
    action = data.get("action")

    logger.info(
        "github_webhook_received",
        event_type=x_github_event,
        action=action,
        repository=data.get("repository", {}).get("full_name"),
    )

    if not should_process_event(x_github_event, action):
        logger.debug("github_event_skipped", event_type=x_github_event, action=action)
        return JSONResponse(
            status_code=200,
            content={"status": "skipped", "reason": "Event type not processed"},
        )

    task_info = extract_task_info(x_github_event, data)
    task_id = str(uuid.uuid4())
    task_info["task_id"] = task_id

    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url)
    await redis_client.lpush("agent:tasks", json.dumps(task_info))
    await redis_client.aclose()

    logger.info("github_task_queued", task_id=task_id, event_type=x_github_event)

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "task_id": task_id},
    )


@router.get("/health")
async def health_check():
    return {"status": "healthy", "webhook": "github"}
