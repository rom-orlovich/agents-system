from typing import Protocol, TypeVar, Generic
from abc import abstractmethod

T = TypeVar("T")


class RepositoryPort(Protocol, Generic[T]):
    @abstractmethod
    async def get(self, id: str) -> T | None: ...

    @abstractmethod
    async def save(self, entity: T) -> T: ...

    @abstractmethod
    async def delete(self, id: str) -> bool: ...

    @abstractmethod
    async def find_by(self, **criteria: str | int | bool) -> list[T]: ...

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[T]: ...
