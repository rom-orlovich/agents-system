import asyncio
import signal
from contextlib import asynccontextmanager
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import redis.asyncio as redis

from config import get_settings
from services.knowledge import KnowledgeService, NoopKnowledgeService

logger = structlog.get_logger(__name__)

shutdown_event = asyncio.Event()


class TaskWorker:
    def __init__(
        self,
        settings: Any,
        knowledge_service: KnowledgeService | NoopKnowledgeService,
    ):
        self._settings = settings
        self._redis: redis.Redis | None = None
        self._running = False
        self._knowledge = knowledge_service

    async def start(self) -> None:
        self._redis = redis.from_url(self._settings.redis_url)
        self._running = True
        logger.info(
            "task_worker_started", max_concurrent=self._settings.max_concurrent_tasks
        )

        semaphore = asyncio.Semaphore(self._settings.max_concurrent_tasks)

        while self._running:
            try:
                task_data = await self._redis.brpop("agent:tasks", timeout=1)
                if task_data:
                    async with semaphore:
                        asyncio.create_task(self._process_task(task_data[1]))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("worker_error", error=str(e))
                await asyncio.sleep(1)

    async def _process_task(self, task_data: bytes) -> None:
        import json

        try:
            task = json.loads(task_data)
            task_id = task.get("task_id", "unknown")
            logger.info("task_started", task_id=task_id)

            await self._update_task_status(task_id, "in_progress")
            result = await self._execute_task(task)
            await self._update_task_status(task_id, "completed", result)

            logger.info("task_completed", task_id=task_id)
        except Exception as e:
            logger.exception("task_failed", error=str(e))
            if "task_id" in locals():
                await self._update_task_status(task_id, "failed", {"error": str(e)})

    async def _execute_task(self, task: dict[str, Any]) -> dict[str, Any]:
        from pathlib import Path
        from cli.factory import run_cli

        prompt = task.get("prompt", "")
        repo_path = task.get("repo_path", "/app/repos/default")
        task_id = task.get("task_id", "unknown")
        agent_type = task.get("agent_type", "")

        model = self._get_model_for_task(agent_type)
        output_queue: asyncio.Queue[str | None] = asyncio.Queue()

        try:
            result = await run_cli(
                prompt=prompt,
                working_dir=Path(repo_path),
                output_queue=output_queue,
                task_id=task_id,
                timeout_seconds=self._settings.task_timeout_seconds,
                model=model,
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.return_code,
            }
        except asyncio.TimeoutError:
            return {"error": "Task timed out", "return_code": -1}

    def _get_model_for_task(self, agent_type: str) -> str | None:
        is_complex_task = agent_type.lower() in (
            "planning",
            "consultation",
            "question_asking",
            "brain",
        )

        if self._settings.cli_provider == "cursor":
            return (
                self._settings.cursor_model_complex
                if is_complex_task
                else self._settings.cursor_model_execution
            )
        elif self._settings.cli_provider == "claude":
            return (
                self._settings.claude_model_complex
                if is_complex_task
                else self._settings.claude_model_execution
            )

        return None

    async def _update_task_status(
        self, task_id: str, status: str, result: dict[str, Any] | None = None
    ) -> None:
        import json

        if self._redis:
            update = {"status": status}
            if result:
                update["result"] = result
            await self._redis.hset(
                f"task:{task_id}", mapping={"data": json.dumps(update)}
            )
            await self._redis.publish(f"task:{task_id}:status", json.dumps(update))

    async def stop(self) -> None:
        self._running = False
        if self._redis:
            await self._redis.aclose()
        logger.info("task_worker_stopped")


worker: TaskWorker | None = None
knowledge_service: KnowledgeService | NoopKnowledgeService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker, knowledge_service
    settings = get_settings()

    if settings.knowledge_services_enabled:
        knowledge_service = KnowledgeService(
            llamaindex_url=settings.llamaindex_url,
            gkg_url=settings.knowledge_graph_url,
            enabled=True,
            timeout=settings.knowledge_timeout_seconds,
            retry_count=settings.knowledge_retry_count,
        )
        status = await knowledge_service.health_check()
        logger.info(
            "knowledge_services_initialized",
            llamaindex_available=status.llamaindex_available,
            gkg_available=status.gkg_available,
        )
    else:
        knowledge_service = NoopKnowledgeService()
        logger.info("knowledge_services_disabled")

    worker = TaskWorker(settings, knowledge_service)

    worker_task = asyncio.create_task(worker.start())

    def handle_shutdown(sig: signal.Signals) -> None:
        logger.info("shutdown_signal_received", signal=sig.name)
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s))

    logger.info(
        "agent_engine_started", port=settings.port, cli_provider=settings.cli_provider
    )
    yield

    await worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    logger.info("agent_engine_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agent Engine",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "agent-engine"}

    @app.get("/health/detailed")
    async def detailed_health_check():
        settings = get_settings()
        result = {
            "status": "healthy",
            "service": "agent-engine",
            "components": {
                "worker": worker._running if worker else False,
                "redis": False,
            },
            "knowledge_services": {
                "enabled": settings.knowledge_services_enabled,
                "available": False,
                "llamaindex": False,
                "gkg": False,
            },
        }

        try:
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            result["components"]["redis"] = True
            await redis_client.aclose()
        except Exception:
            result["status"] = "degraded"

        if knowledge_service:
            ks_status = await knowledge_service.health_check()
            result["knowledge_services"]["available"] = knowledge_service.is_available
            result["knowledge_services"]["llamaindex"] = ks_status.llamaindex_available
            result["knowledge_services"]["gkg"] = ks_status.gkg_available

        return result

    @app.get("/status")
    async def get_status():
        settings = get_settings()
        return {
            "service": "agent-engine",
            "cli_provider": settings.cli_provider,
            "max_concurrent_tasks": settings.max_concurrent_tasks,
            "worker_running": worker._running if worker else False,
            "knowledge_services_enabled": settings.knowledge_services_enabled,
            "knowledge_available": (
                knowledge_service.is_available if knowledge_service else False
            ),
        }

    @app.post("/knowledge/toggle")
    async def toggle_knowledge_services(enabled: bool):
        if knowledge_service is None:
            return JSONResponse(
                status_code=400,
                content={"error": "Knowledge service not initialized"},
            )

        if enabled:
            knowledge_service.enable()
        else:
            knowledge_service.disable()

        return {
            "knowledge_services_enabled": enabled,
            "message": f"Knowledge services {'enabled' if enabled else 'disabled'}",
        }

    @app.post("/tasks")
    async def create_task(task: dict[str, Any]):
        import json
        import uuid

        settings = get_settings()
        redis_client = redis.from_url(settings.redis_url)

        task_id = str(uuid.uuid4())
        task["task_id"] = task_id

        await redis_client.lpush("agent:tasks", json.dumps(task))
        await redis_client.aclose()

        return JSONResponse(
            status_code=202,
            content={"task_id": task_id, "status": "queued"},
        )

    @app.get("/tasks/{task_id}")
    async def get_task(task_id: str):
        import json

        settings = get_settings()
        redis_client = redis.from_url(settings.redis_url)

        data = await redis_client.hget(f"task:{task_id}", "data")
        await redis_client.aclose()

        if data:
            return json.loads(data)
        return JSONResponse(status_code=404, content={"error": "Task not found"})

    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
    )
