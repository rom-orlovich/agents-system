import json
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis
import structlog

from config import settings

logger = structlog.get_logger()

_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def publish_knowledge_event(
    event_type: str,
    task_id: str | None,
    data: dict[str, Any],
) -> None:
    if not settings.publish_knowledge_events:
        return

    if not task_id:
        logger.debug("skipping_knowledge_event_no_task_id", event_type=event_type)
        return

    try:
        client = await get_redis_client()
        event = {
            "type": event_type,
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps(data),
        }
        await client.xadd("task_events", event)
        logger.debug(
            "knowledge_event_published", event_type=event_type, task_id=task_id
        )
    except Exception as e:
        logger.warning("knowledge_event_publish_failed", error=str(e))


async def publish_query_event(
    task_id: str | None,
    tool_name: str,
    query: str,
    org_id: str,
    source_types: list[str] | None = None,
) -> None:
    await publish_knowledge_event(
        "knowledge:query",
        task_id,
        {
            "tool_name": tool_name,
            "query": query,
            "org_id": org_id,
            "source_types": source_types or [],
        },
    )


async def publish_result_event(
    task_id: str | None,
    tool_name: str,
    query: str,
    results_count: int,
    results_preview: list[dict[str, Any]],
    query_time_ms: float,
    cached: bool = False,
) -> None:
    await publish_knowledge_event(
        "knowledge:result",
        task_id,
        {
            "tool_name": tool_name,
            "query": query,
            "results_count": results_count,
            "results_preview": results_preview[:5],
            "query_time_ms": query_time_ms,
            "cached": cached,
        },
    )


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
