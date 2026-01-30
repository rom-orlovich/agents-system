import asyncio
import structlog
from collections import deque
from ports.queue import QueuePort, TaskQueueMessage

logger = structlog.get_logger()


class MemoryQueueAdapter:
    def __init__(self) -> None:
        self._queue: deque[TaskQueueMessage] = deque()
        self._condition = asyncio.Condition()

    async def enqueue(self, message: TaskQueueMessage) -> None:
        async with self._condition:
            self._queue.append(message)
            self._queue = deque(
                sorted(self._queue, key=lambda m: m.priority, reverse=True)
            )
            self._condition.notify()
            logger.info("message_enqueued", task_id=message.task_id)

    async def dequeue(self, timeout: float) -> TaskQueueMessage | None:
        async with self._condition:
            try:
                await asyncio.wait_for(
                    self._condition.wait_for(lambda: len(self._queue) > 0),
                    timeout=timeout,
                )
                return self._queue.popleft()
            except asyncio.TimeoutError:
                return None

    async def get_queue_length(self) -> int:
        async with self._condition:
            return len(self._queue)
