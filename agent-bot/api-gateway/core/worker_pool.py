import asyncio
import structlog
from typing import TypeVar, Callable, Awaitable, List
from dataclasses import dataclass

logger = structlog.get_logger()

T = TypeVar("T")


@dataclass
class WorkerResult:
    success: bool
    result: T | None
    error: str | None


class WorkerPool:
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.logger = structlog.get_logger(worker_pool=True)

    async def execute_parallel(
        self,
        tasks: List[Callable[[], Awaitable[T]]],
        task_names: List[str] | None = None,
    ) -> List[WorkerResult]:
        if task_names is None:
            task_names = [f"task_{i}" for i in range(len(tasks))]

        if len(task_names) != len(tasks):
            raise ValueError("task_names must match tasks length")

        self.logger.info("worker_pool_executing", total_tasks=len(tasks))

        results = await asyncio.gather(
            *[
                self._execute_with_semaphore(task, name)
                for task, name in zip(tasks, task_names)
            ],
            return_exceptions=True,
        )

        return [
            result if isinstance(result, WorkerResult) else WorkerResult(False, None, str(result))
            for result in results
        ]

    async def _execute_with_semaphore(
        self, task: Callable[[], Awaitable[T]], name: str
    ) -> WorkerResult:
        async with self.semaphore:
            try:
                self.logger.debug("worker_executing", task=name)
                result = await task()
                self.logger.debug("worker_completed", task=name)
                return WorkerResult(success=True, result=result, error=None)
            except Exception as e:
                self.logger.error("worker_failed", task=name, error=str(e))
                return WorkerResult(success=False, result=None, error=str(e))


class ParallelRequestHandler:
    def __init__(self, max_concurrent: int = 10):
        self.worker_pool = WorkerPool(max_workers=max_concurrent)

    async def handle_batch(
        self,
        requests: List[dict],
        handler: Callable[[dict], Awaitable[T]],
    ) -> List[WorkerResult]:
        tasks = [lambda req=req: handler(req) for req in requests]
        task_names = [f"request_{i}" for i in range(len(requests))]

        return await self.worker_pool.execute_parallel(tasks, task_names)
