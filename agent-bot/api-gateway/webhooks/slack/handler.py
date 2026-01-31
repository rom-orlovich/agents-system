import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import structlog

from config import get_settings
from .events import should_process_event, extract_task_info

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/webhooks/slack", tags=["slack-webhook"])


@router.post("")
async def handle_slack_webhook(request: Request):
    payload = await request.body()
    data = json.loads(payload)

    if data.get("type") == "url_verification":
        return JSONResponse(content={"challenge": data.get("challenge")})

    event = data.get("event", {})
    team_id = data.get("team_id", "")

    logger.info(
        "slack_webhook_received",
        event_type=event.get("type"),
        channel=event.get("channel"),
    )

    if not should_process_event(event):
        logger.debug("slack_event_skipped", event_type=event.get("type"))
        return JSONResponse(
            status_code=200,
            content={"status": "skipped", "reason": "Event not processed"},
        )

    task_info = extract_task_info(event, team_id)
    task_id = str(uuid.uuid4())
    task_info["task_id"] = task_id

    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url)
    await redis_client.lpush("agent:tasks", json.dumps(task_info))
    await redis_client.aclose()

    logger.info("slack_task_queued", task_id=task_id, channel=event.get("channel"))

    return JSONResponse(status_code=200, content={"status": "accepted"})


@router.get("/health")
async def health_check():
    return {"status": "healthy", "webhook": "slack"}
