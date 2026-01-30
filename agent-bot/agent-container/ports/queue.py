from typing import Protocol
from abc import abstractmethod
from pydantic import BaseModel, ConfigDict


class TaskQueueMessage(BaseModel):
    model_config = ConfigDict(strict=True)

    task_id: str
    installation_id: str
    input_message: str
    model: str
    priority: int = 2
    source_metadata: dict[str, str | int]


class QueuePort(Protocol):
    @abstractmethod
    async def enqueue(self, message: TaskQueueMessage) -> None: ...

    @abstractmethod
    async def dequeue(self, timeout: float) -> TaskQueueMessage | None: ...

    @abstractmethod
    async def acknowledge(self, message_id: str) -> None: ...

    @abstractmethod
    async def get_queue_length(self) -> int: ...
