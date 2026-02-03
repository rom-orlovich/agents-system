import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone

import redis.asyncio as redis

from config import settings
from logger import TaskLogger
from models import TaskEventType

logger = logging.getLogger(__name__)

loggers_cache: dict[str, TaskLogger] = {}
webhook_buffer: dict[str, list[dict]] = defaultdict(list)
running = True


def get_or_create_logger(task_id: str) -> TaskLogger:
    if task_id not in loggers_cache:
        loggers_cache[task_id] = TaskLogger(task_id, settings.logs_dir)
    return loggers_cache[task_id]


async def process_webhook_event(event: dict):
    webhook_event_id = event.get("webhook_event_id")
    event_type = event.get("type")
    data = event.get("data", {})
    timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())

    if isinstance(data, str):
        data = json.loads(data)

    task_id = data.get("task_id")

    if not task_id:
        webhook_buffer[webhook_event_id].append(
            {
                "timestamp": timestamp,
                "stage": event_type.split(":")[1],
                "data": data,
            }
        )
        return

    task_logger = get_or_create_logger(task_id)

    for buffered in webhook_buffer.pop(webhook_event_id, []):
        task_logger.append_webhook_event(buffered)

    task_logger.append_webhook_event(
        {"timestamp": timestamp, "stage": event_type.split(":")[1], "data": data}
    )


async def process_task_event(event: dict):
    task_id = event.get("task_id")
    if not task_id:
        logger.warning("task_event_missing_id", event=event)
        return

    event_type = event.get("type")
    data = event.get("data", {})
    timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())

    if isinstance(data, str):
        data = json.loads(data)

    task_logger = get_or_create_logger(task_id)

    if event_type == TaskEventType.TASK_CREATED:
        task_logger.write_metadata(data)
        task_logger.write_input({"message": data.get("input_message")})

    elif event_type == TaskEventType.TASK_OUTPUT:
        task_logger.append_agent_output(
            {"timestamp": timestamp, "type": "output", "content": data.get("content")}
        )

    elif event_type == TaskEventType.TASK_USER_INPUT:
        task_logger.append_user_input(
            {
                "timestamp": timestamp,
                "type": "user_response",
                "question_type": data.get("question_type", "clarification"),
                "content": data.get("content"),
            }
        )

    elif event_type == TaskEventType.TASK_COMPLETED:
        task_logger.write_final_result(
            {
                "success": True,
                "result": data.get("result"),
                "metrics": {
                    "cost_usd": data.get("cost_usd"),
                    "duration_seconds": data.get("duration_seconds"),
                },
                "completed_at": timestamp,
            }
        )

    elif event_type == TaskEventType.TASK_FAILED:
        task_logger.write_final_result(
            {"success": False, "error": data.get("error"), "completed_at": timestamp}
        )


async def process_knowledge_event(event: dict):
    task_id = event.get("task_id")
    if not task_id:
        logger.warning("knowledge_event_missing_task_id", event=event)
        return

    event_type = event.get("type")
    data = event.get("data", {})
    timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())

    if isinstance(data, str):
        data = json.loads(data)

    task_logger = get_or_create_logger(task_id)

    if event_type == TaskEventType.KNOWLEDGE_QUERY:
        task_logger.append_knowledge_interaction(
            {
                "timestamp": timestamp,
                "type": "query",
                "tool_name": data.get("tool_name", "unknown"),
                "query": data.get("query", ""),
                "source_types": data.get("source_types", []),
                "org_id": data.get("org_id"),
            }
        )

    elif event_type == TaskEventType.KNOWLEDGE_RESULT:
        task_logger.append_knowledge_interaction(
            {
                "timestamp": timestamp,
                "type": "result",
                "tool_name": data.get("tool_name", "unknown"),
                "query": data.get("query", ""),
                "results_count": data.get("results_count", 0),
                "results_preview": data.get("results_preview", [])[:5],
                "query_time_ms": data.get("query_time_ms", 0.0),
                "cached": data.get("cached", False),
            }
        )

    elif event_type == TaskEventType.KNOWLEDGE_TOOL_CALL:
        task_logger.append_knowledge_interaction(
            {
                "timestamp": timestamp,
                "type": "tool_call",
                "tool_name": data.get("tool_name", "unknown"),
                "parameters": data.get("parameters", {}),
            }
        )

    elif event_type == TaskEventType.KNOWLEDGE_CONTEXT_USED:
        task_logger.append_knowledge_interaction(
            {
                "timestamp": timestamp,
                "type": "context_used",
                "tool_name": data.get("tool_name", "unknown"),
                "contexts_count": data.get("contexts_count", 0),
                "relevance_scores": data.get("relevance_scores", []),
                "total_tokens": data.get("total_tokens"),
            }
        )


async def process_event(event: dict):
    event_type = event.get("type")

    if event_type.startswith("webhook:"):
        await process_webhook_event(event)
    elif event_type.startswith("task:"):
        await process_task_event(event)
    elif event_type.startswith("knowledge:"):
        await process_knowledge_event(event)
    else:
        logger.warning("unknown_event_type", event_type=event_type)


async def run():
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    try:
        await redis_client.xgroup_create(
            settings.redis_stream, settings.redis_consumer_group, id="0", mkstream=True
        )
        logger.info("consumer_group_created", group=settings.redis_consumer_group)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
        logger.info("consumer_group_exists", group=settings.redis_consumer_group)

    logger.info("worker_started", stream=settings.redis_stream)

    while running:
        try:
            events = await redis_client.xreadgroup(
                groupname=settings.redis_consumer_group,
                consumername="worker-1",
                streams={settings.redis_stream: ">"},
                count=settings.max_batch_size,
                block=5000,
            )

            for stream_name, messages in events:
                for message_id, event_data in messages:
                    try:
                        await process_event(event_data)
                        await redis_client.xack(
                            settings.redis_stream,
                            settings.redis_consumer_group,
                            message_id,
                        )
                    except Exception as e:
                        logger.error(
                            "event_processing_failed",
                            message_id=message_id,
                            error=str(e),
                            exc_info=True,
                        )

        except asyncio.CancelledError:
            logger.info("worker_cancelled")
            break
        except Exception as e:
            logger.error("worker_error", error=str(e), exc_info=True)
            await asyncio.sleep(5)

    await redis_client.close()
    logger.info("worker_stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(run())
