from typing import Protocol
from abc import abstractmethod


class DatabasePort(Protocol):
    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def execute(
        self, query: str, params: dict[str, str | int | bool] | None = None
    ) -> list[dict[str, str | int | bool]]:
        ...

    @abstractmethod
    async def fetch_one(
        self, query: str, params: dict[str, str | int | bool] | None = None
    ) -> dict[str, str | int | bool] | None:
        ...
