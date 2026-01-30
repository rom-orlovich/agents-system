import asyncio
from collections import deque
from ports import QueuePort, TaskQueueMessage


class MemoryQueueAdapter:
    def __init__(self):
        self._queue: deque[tuple[TaskQueueMessage, int]] = deque()
        self._condition = asyncio.Condition()

    async def enqueue(self, message: TaskQueueMessage) -> None:
        async with self._condition:
            self._queue.append((message, message.priority))
            self._queue = deque(
                sorted(self._queue, key=lambda x: x[1])
            )
            self._condition.notify()

    async def dequeue(self, timeout: float) -> TaskQueueMessage | None:
        async with self._condition:
            try:
                await asyncio.wait_for(
                    self._condition.wait_for(lambda: len(self._queue) > 0),
                    timeout=timeout,
                )
                message, priority = self._queue.popleft()
                return message
            except asyncio.TimeoutError:
                return None

    async def acknowledge(self, message_id: str) -> None:
        pass

    async def get_queue_length(self) -> int:
        return len(self._queue)
