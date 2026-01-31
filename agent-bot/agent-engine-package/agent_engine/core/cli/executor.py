import asyncio
from pathlib import Path
from typing import TypeVar

from agent_engine.core.cli.base import CLIResult, CLIProvider
from agent_engine.core.config import settings, CLIProviderType

T = TypeVar("T", bound=CLIProvider)


class CLIExecutor:
    def __init__(self, provider_type: CLIProviderType | None = None) -> None:
        self.provider_type = provider_type or settings.cli_provider
        self.provider = self._load_provider()

    def _load_provider(self) -> CLIProvider:
        if self.provider_type == CLIProviderType.CLAUDE:
            from agent_engine.core.cli.providers.claude.runner import ClaudeCLIRunner
            return ClaudeCLIRunner()
        elif self.provider_type == CLIProviderType.CURSOR:
            from agent_engine.core.cli.providers.cursor.runner import CursorCLIRunner
            return CursorCLIRunner()

        raise ValueError(f"Unknown CLI provider: {self.provider_type}")

    async def execute(
        self,
        prompt: str,
        working_dir: Path,
        task_id: str,
        output_queue: asyncio.Queue[str | None] | None = None,
        timeout_seconds: int | None = None,
        model: str | None = None,
        allowed_tools: str | None = None,
        agents: str | None = None,
        debug_mode: str | None = None,
    ) -> CLIResult:
        if output_queue is None:
            output_queue = asyncio.Queue()

        return await self.provider.run(
            prompt=prompt,
            working_dir=working_dir,
            output_queue=output_queue,
            task_id=task_id,
            timeout_seconds=timeout_seconds or settings.task_timeout_seconds,
            model=model,
            allowed_tools=allowed_tools or settings.default_allowed_tools,
            agents=agents,
            debug_mode=debug_mode,
        )

    def get_provider_name(self) -> str:
        return self.provider_type.value
