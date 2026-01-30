from typing import Protocol
from pydantic import BaseModel, ConfigDict


class CLIResult(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    output: str
    error: str | None
    cost_usd: float
    input_tokens: int
    output_tokens: int


class CLIRunner(Protocol):
    async def execute(
        self, prompt: str, working_dir: str, model: str, agents: list[str]
    ) -> CLIResult:
        ...
