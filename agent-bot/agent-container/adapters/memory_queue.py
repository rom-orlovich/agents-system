import asyncio
from collections import deque

import structlog

from ports import TaskQueueMessage

logger = structlog.get_logger()


class InMemoryQueueAdapter:
    def __init__(self) -> None:
        self._queue: deque[TaskQueueMessage] = deque()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def enqueue(self, message: TaskQueueMessage) -> None:
        async with self._lock:
            self._queue.append(message)
            self._not_empty.set()
            logger.info("task_enqueued", task_id=message.task_id)

    async def dequeue(self, timeout_seconds: float = 30.0) -> TaskQueueMessage | None:
        try:
            await asyncio.wait_for(self._not_empty.wait(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            return None

        async with self._lock:
            if not self._queue:
                self._not_empty.clear()
                return None

            message = self._queue.popleft()

            if not self._queue:
                self._not_empty.clear()

            logger.info("task_dequeued", task_id=message.task_id)
            return message

    async def ack(self, task_id: str) -> None:
        logger.info("task_acked", task_id=task_id)

    async def nack(self, task_id: str) -> None:
        logger.info("task_nacked", task_id=task_id)

    async def get_queue_size(self) -> int:
        async with self._lock:
            return len(self._queue)
