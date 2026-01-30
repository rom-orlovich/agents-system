from typing import Protocol
from abc import abstractmethod
from pathlib import Path


class CLIRunnerPort(Protocol):
    @abstractmethod
    async def run_task(
        self,
        task_description: str,
        repo_path: Path,
        context: dict[str, str | int | bool],
    ) -> dict[str, str | bool]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
