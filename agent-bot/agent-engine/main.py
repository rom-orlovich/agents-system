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

logger = structlog.get_logger(__name__)

shutdown_event = asyncio.Event()


class TaskWorker:
    def __init__(self, settings: Any):
        self._settings = settings
        self._redis: redis.Redis | None = None
        self._running = False

    async def start(self) -> None:
        self._redis = redis.from_url(self._settings.redis_url)
        self._running = True
        logger.info("task_worker_started", max_concurrent=self._settings.max_concurrent_tasks)

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
        import subprocess
        import json

        prompt = task.get("prompt", "")
        repo_path = task.get("repo_path", "/app/repos/default")
        cli_provider = self._settings.cli_provider

        if cli_provider == "claude":
            cmd = ["claude", "--print", "--output-format", "json", prompt]
        else:
            cmd = ["cursor", "--print", prompt]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._settings.task_timeout_seconds,
            )
            return {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "return_code": process.returncode,
            }
        except asyncio.TimeoutError:
            return {"error": "Task timed out", "return_code": -1}

    async def _update_task_status(
        self, task_id: str, status: str, result: dict[str, Any] | None = None
    ) -> None:
        import json
        if self._redis:
            update = {"status": status}
            if result:
                update["result"] = result
            await self._redis.hset(f"task:{task_id}", mapping={"data": json.dumps(update)})
            await self._redis.publish(f"task:{task_id}:status", json.dumps(update))

    async def stop(self) -> None:
        self._running = False
        if self._redis:
            await self._redis.aclose()
        logger.info("task_worker_stopped")


worker: TaskWorker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker
    settings = get_settings()
    worker = TaskWorker(settings)

    worker_task = asyncio.create_task(worker.start())

    def handle_shutdown(sig: signal.Signals) -> None:
        logger.info("shutdown_signal_received", signal=sig.name)
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s))

    logger.info("agent_engine_started", port=settings.port, cli_provider=settings.cli_provider)
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

    @app.get("/status")
    async def get_status():
        settings = get_settings()
        return {
            "service": "agent-engine",
            "cli_provider": settings.cli_provider,
            "max_concurrent_tasks": settings.max_concurrent_tasks,
            "worker_running": worker._running if worker else False,
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
