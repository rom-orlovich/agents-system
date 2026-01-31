import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Awaitable, Any
import json
import structlog

from agent_engine.core.config import settings
from agent_engine.core.cli.executor import CLIExecutor
from agent_engine.core.queue_manager import QueueManager, TaskStatus

logger = structlog.get_logger()

TaskCallback = Callable[[str, str, bool, float], Awaitable[None]]


class TaskWorker:
    def __init__(
        self,
        queue_manager: QueueManager | None = None,
        cli_executor: CLIExecutor | None = None,
        max_concurrent_tasks: int | None = None,
        working_dir: Path | None = None,
        on_task_complete: TaskCallback | None = None,
    ) -> None:
        self.queue_manager = queue_manager or QueueManager()
        self.cli_executor = cli_executor or CLIExecutor()
        self.max_concurrent_tasks = max_concurrent_tasks or settings.max_concurrent_tasks
        self.working_dir = working_dir or settings.app_dir
        self.on_task_complete = on_task_complete

        self.running = False
        self.semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        self.active_tasks: set[asyncio.Task[None]] = set()

    async def run(self) -> None:
        self.running = True
        logger.info(
            "task_worker_started",
            max_concurrent_tasks=self.max_concurrent_tasks,
        )

        while self.running:
            try:
                task_id = await self.queue_manager.pop_task(timeout=5)

                if task_id:
                    logger.info("task_queued_for_processing", task_id=task_id)

                    task = asyncio.create_task(self._process_with_semaphore(task_id))
                    self.active_tasks.add(task)
                    task.add_done_callback(self.active_tasks.discard)

                else:
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error("worker_error", error=str(e))
                await asyncio.sleep(5)

        logger.info("task_worker_stopped")

    async def stop(self) -> None:
        logger.info("stopping_task_worker")
        self.running = False

    async def wait_for_active_tasks(self, timeout: int = 30) -> None:
        if not self.active_tasks:
            return

        logger.info(
            "waiting_for_active_tasks",
            active_count=len(self.active_tasks),
            timeout=timeout,
        )

        try:
            await asyncio.wait_for(
                asyncio.gather(*self.active_tasks, return_exceptions=True),
                timeout=timeout,
            )
            logger.info("all_active_tasks_completed")
        except asyncio.TimeoutError:
            logger.warning(
                "active_tasks_timeout",
                remaining=len(self.active_tasks),
            )

    async def _process_with_semaphore(self, task_id: str) -> None:
        async with self.semaphore:
            logger.debug(
                "task_acquired_semaphore",
                task_id=task_id,
                active_tasks=self.max_concurrent_tasks - self.semaphore._value,
            )
            await self._process_task(task_id)

    async def _process_task(self, task_id: str) -> None:
        await self.queue_manager.set_task_status(task_id, TaskStatus.RUNNING)

        task_data_str = await self.queue_manager.get_task_data(task_id)
        if not task_data_str:
            logger.error("task_data_not_found", task_id=task_id)
            await self.queue_manager.set_task_status(task_id, TaskStatus.FAILED)
            return

        task_data = json.loads(task_data_str)
        prompt = task_data.get("prompt", "")
        agent_type = task_data.get("agent_type", "brain")
        model = settings.get_model_for_agent(agent_type)

        output_queue: asyncio.Queue[str | None] = asyncio.Queue()

        output_chunks: list[str] = []

        async def stream_output() -> None:
            while True:
                chunk = await output_queue.get()
                if chunk is None:
                    break
                output_chunks.append(chunk)
                await self.queue_manager.append_output(task_id, chunk)

        try:
            init_log = self._build_init_log(task_id, agent_type, model)
            await self.queue_manager.append_output(task_id, init_log)

            result, _ = await asyncio.gather(
                self.cli_executor.execute(
                    prompt=prompt,
                    working_dir=self.working_dir,
                    output_queue=output_queue,
                    task_id=task_id,
                    model=model,
                ),
                stream_output(),
            )

            if result.success:
                await self.queue_manager.set_task_status(task_id, TaskStatus.COMPLETED)
                logger.info(
                    "task_completed",
                    task_id=task_id,
                    cost_usd=result.cost_usd,
                )
            else:
                await self.queue_manager.set_task_status(task_id, TaskStatus.FAILED)
                logger.warning(
                    "task_failed",
                    task_id=task_id,
                    error=result.error,
                )

            if self.on_task_complete:
                await self.on_task_complete(
                    task_id,
                    result.clean_output or result.output,
                    result.success,
                    result.cost_usd,
                )

        except Exception as e:
            await self.queue_manager.set_task_status(task_id, TaskStatus.FAILED)
            logger.error("task_processing_error", task_id=task_id, error=str(e))

            if self.on_task_complete:
                await self.on_task_complete(task_id, str(e), False, 0.0)

    def _build_init_log(self, task_id: str, agent_type: str, model: str) -> str:
        now = datetime.now(timezone.utc).isoformat()
        return (
            f"[SYSTEM] Task {task_id} started at {now}\n"
            f"[SYSTEM] Agent: {agent_type} | Model: {model}\n"
            f"[SYSTEM] Starting CLI...\n"
        )
