"""Base CLI executor interface."""

from abc import ABC, abstractmethod
from typing import Any


class CLIExecutor(ABC):
    """Abstract base class for CLI executors."""

    @abstractmethod
    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute task using CLI tool."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if CLI is available."""
        pass
