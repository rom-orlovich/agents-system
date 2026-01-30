from typing import Protocol
from abc import abstractmethod
from pydantic import BaseModel, ConfigDict


class TaskQueueMessage(BaseModel):
    model_config = ConfigDict(strict=True)

    task_id: str
    organization_id: str
    provider: str
    payload: dict[str, str | int | bool | dict[str, str]]
    priority: int = 0


class QueuePort(Protocol):
    @abstractmethod
    async def enqueue(self, message: TaskQueueMessage) -> None:
        ...

    @abstractmethod
    async def dequeue(self, timeout: float) -> TaskQueueMessage | None:
        ...

    @abstractmethod
    async def get_queue_length(self) -> int:
        ...
