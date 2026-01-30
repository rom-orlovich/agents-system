from typing import Protocol

from pydantic import BaseModel, ConfigDict


class CLIExecutionResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool
    output: str
    error: str | None
    exit_code: int
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0


class CLIRunnerPort(Protocol):
    async def execute_and_wait(
        self,
        command: list[str],
        input_text: str,
        timeout_seconds: int,
    ) -> CLIExecutionResult: ...

    async def execute_streaming(
        self,
        command: list[str],
        input_text: str,
    ): ...
