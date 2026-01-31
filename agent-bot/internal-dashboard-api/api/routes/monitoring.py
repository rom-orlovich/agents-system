import asyncio
from typing import Annotated

from fastapi import APIRouter, WebSocket, Query
import redis.asyncio as redis
import structlog

from config import get_settings
from services import TaskManager, AgentManager

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])
logger = structlog.get_logger(__name__)


@router.get("/overview")
async def get_overview():
    task_manager = TaskManager()
    agent_manager = AgentManager()

    try:
        tasks_stats = await task_manager.get_task_stats()
        agent_metrics = await agent_manager.get_agent_metrics()

        return {
            "tasks": tasks_stats,
            "agents": agent_metrics,
        }
    finally:
        await task_manager.close()
        await agent_manager.close()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    task_id: Annotated[str | None, Query()] = None,
):
    await websocket.accept()
    settings = get_settings()

    try:
        redis_client = redis.from_url(settings.redis_url)
        pubsub = redis_client.pubsub()

        if task_id:
            await pubsub.subscribe(f"task:{task_id}:status")
        else:
            await pubsub.psubscribe("task:*:status")

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                await websocket.send_json({
                    "channel": message.get("channel", b"").decode(),
                    "data": message.get("data", b"").decode(),
                })
            await asyncio.sleep(0.1)

    except Exception as e:
        logger.exception("websocket_error", error=str(e))
    finally:
        await pubsub.unsubscribe()
        await redis_client.aclose()
        await websocket.close()


@router.get("/health")
async def health_check():
    task_manager = TaskManager()
    agent_manager = AgentManager()

    try:
        redis_ok = True
        agent_ok = True

        try:
            await task_manager.get_queue_length()
        except Exception:
            redis_ok = False

        try:
            await agent_manager.get_agent_health()
        except Exception:
            agent_ok = False

        status = "healthy" if redis_ok and agent_ok else "degraded"

        return {
            "status": status,
            "components": {
                "redis": "healthy" if redis_ok else "unhealthy",
                "agent_engine": "healthy" if agent_ok else "unhealthy",
            },
        }
    finally:
        await task_manager.close()
        await agent_manager.close()
