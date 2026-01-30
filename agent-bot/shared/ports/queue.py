from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class TaskPriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskQueueMessage(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    task_id: str
    installation_id: str
    provider: str
    input_message: str
    priority: TaskPriority
    source_metadata: dict[str, str]
    created_at: datetime


class QueuePort(Protocol):
    async def enqueue(self, message: TaskQueueMessage) -> None: ...
    async def dequeue(self, timeout_seconds: float = 30.0) -> TaskQueueMessage | None: ...
    async def ack(self, task_id: str) -> None: ...
    async def nack(self, task_id: str) -> None: ...
    async def get_queue_size(self) -> int: ...
