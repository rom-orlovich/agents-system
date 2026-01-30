import asyncio
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Dict, Any
import json


logger = structlog.get_logger()


class StreamingLogger:
    def __init__(self, task_id: str, logs_base_dir: Path | None = None):
        self.task_id = task_id
        self.logs_base_dir = logs_base_dir or Path("/data/logs/tasks")
        self.task_dir = self.logs_base_dir / task_id
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.stream_file = self.task_dir / "stream.jsonl"
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def log(self, event_type: str, **data: Any) -> None:
        if self._closed:
            return

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **data,
        }

        with open(self.stream_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        await self._queue.put(log_entry)

    async def stream(self) -> AsyncIterator[Dict[str, Any]]:
        while not self._closed or not self._queue.empty():
            try:
                entry = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                yield entry
            except asyncio.TimeoutError:
                continue

    async def log_progress(self, stage: str, message: str, **extra: Any) -> None:
        await self.log(
            event_type="progress", stage=stage, message=message, **extra
        )

    async def log_cli_output(self, line: str, stream: str = "stdout") -> None:
        await self.log(event_type="cli_output", line=line, stream=stream)

    async def log_mcp_call(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        await self.log(
            event_type="mcp_call", tool_name=tool_name, arguments=arguments
        )

    async def log_mcp_result(
        self, tool_name: str, success: bool, result: Any = None
    ) -> None:
        await self.log(
            event_type="mcp_result",
            tool_name=tool_name,
            success=success,
            result=result,
        )

    async def log_error(self, error: str, **context: Any) -> None:
        await self.log(event_type="error", error=error, **context)

    async def log_completion(
        self, success: bool, result: str | None = None, error: str | None = None
    ) -> None:
        await self.log(
            event_type="completion", success=success, result=result, error=error
        )
        await self.close()

    async def close(self) -> None:
        self._closed = True
        await self._queue.join()
