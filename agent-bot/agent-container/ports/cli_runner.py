from typing import Protocol, AsyncIterator
from abc import abstractmethod
from pydantic import BaseModel, ConfigDict


class CLIOutput(BaseModel):
    model_config = ConfigDict(strict=True)

    output: str
    error: str | None
    success: bool
    cost_usd: float
    input_tokens: int
    output_tokens: int


class CLIRunnerPort(Protocol):
    @abstractmethod
    async def execute(
        self,
        prompt: str,
        model: str,
        working_dir: str,
        agents: list[str] = [],
    ) -> CLIOutput: ...

    @abstractmethod
    async def cancel(self, execution_id: str) -> None: ...

    @abstractmethod
    async def stream_output(
        self, prompt: str, model: str, working_dir: str
    ) -> AsyncIterator[str]: ...
