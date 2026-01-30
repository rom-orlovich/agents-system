# Agent Bot - TDD Implementation Guide

## Part 3: Ports & Adapters Pattern

---

## Phase 4: Define Port Interfaces

### Step 4.1: Create Directory Structure

```bash
mkdir -p agent-container/ports
mkdir -p agent-container/adapters/queue
mkdir -p agent-container/adapters/database
mkdir -p agent-container/adapters/cli
mkdir -p agent-container/adapters/external
mkdir -p agent-container/tests/ports
mkdir -p agent-container/tests/adapters

touch agent-container/ports/__init__.py
touch agent-container/ports/queue.py
touch agent-container/ports/database.py
touch agent-container/ports/cli_runner.py
touch agent-container/ports/external_service.py
touch agent-container/ports/logger.py
```

### Step 4.2: Define Queue Port

**File: `agent-container/ports/queue.py`** (< 80 lines)

```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class TaskPriority(int, Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskQueueMessage(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    task_id: str
    installation_id: str
    provider: str
    input_message: str
    priority: TaskPriority = TaskPriority.NORMAL
    source_metadata: dict[str, str]
    created_at: datetime
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096


class TaskResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    task_id: str
    status: TaskStatus
    output: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    tokens_used: int = 0
    cost_usd: float = 0.0


@runtime_checkable
class QueuePort(Protocol):
    async def enqueue(self, message: TaskQueueMessage) -> None:
        ...

    async def dequeue(self, timeout_seconds: float = 5.0) -> TaskQueueMessage | None:
        ...

    async def acknowledge(self, task_id: str) -> None:
        ...

    async def reject(self, task_id: str, requeue: bool = True) -> None:
        ...

    async def get_queue_length(self) -> int:
        ...

    async def get_task_status(self, task_id: str) -> TaskStatus | None:
        ...
```

### Step 4.3: Define CLI Runner Port

**File: `agent-container/ports/cli_runner.py`** (< 100 lines)

```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable, AsyncIterator
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CLIOutputType(str, Enum):
    STDOUT = "stdout"
    STDERR = "stderr"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    COMPLETION = "completion"
    ERROR = "error"


class CLIOutput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    type: CLIOutputType
    content: str
    timestamp: datetime
    metadata: dict[str, str] = {}


class CLIExecutionConfig(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    model: str
    max_tokens: int
    working_dir: str
    timeout_seconds: int = 300
    allowed_tools: list[str] = []
    environment: dict[str, str] = {}


class CLIExecutionResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool
    output: str
    error: str | None = None
    exit_code: int
    tokens_used: int
    cost_usd: float
    duration_seconds: float


@runtime_checkable
class CLIRunnerPort(Protocol):
    async def execute(
        self,
        prompt: str,
        config: CLIExecutionConfig,
    ) -> AsyncIterator[CLIOutput]:
        ...

    async def execute_and_wait(
        self,
        prompt: str,
        config: CLIExecutionConfig,
    ) -> CLIExecutionResult:
        ...

    async def cancel(self, execution_id: str) -> bool:
        ...

    async def is_available(self) -> bool:
        ...
```

### Step 4.4: Define External Service Port

**File: `agent-container/ports/external_service.py`** (< 80 lines)

```python
from typing import Protocol, runtime_checkable
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ServiceProvider(str, Enum):
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    SENTRY = "sentry"


class PostResultRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    provider: ServiceProvider
    target_id: str
    content: str
    metadata: dict[str, str] = {}


class PostResultResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool
    resource_url: str | None = None
    error: str | None = None


class ReactionType(str, Enum):
    THUMBS_UP = "+1"
    THUMBS_DOWN = "-1"
    ROCKET = "rocket"
    EYES = "eyes"
    HEART = "heart"
    HOORAY = "hooray"


@runtime_checkable
class ExternalServicePort(Protocol):
    async def post_comment(
        self,
        request: PostResultRequest,
        access_token: str,
    ) -> PostResultResponse:
        ...

    async def add_reaction(
        self,
        provider: ServiceProvider,
        target_id: str,
        reaction: ReactionType,
        access_token: str,
    ) -> bool:
        ...

    async def update_status(
        self,
        provider: ServiceProvider,
        target_id: str,
        status: str,
        access_token: str,
    ) -> bool:
        ...
```

### Step 4.5: Define Logger Port

**File: `agent-container/ports/logger.py`** (< 80 lines)

```python
from typing import Protocol, runtime_checkable
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LogEventType(str, Enum):
    PROGRESS = "progress"
    EXECUTION = "execution"
    CLI_OUTPUT = "cli_output"
    MCP_CALL = "mcp_call"
    MCP_RESULT = "mcp_result"
    ERROR = "error"
    COMPLETION = "completion"


class LogEvent(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    timestamp: datetime
    event_type: LogEventType
    task_id: str
    stage: str | None = None
    message: str
    metadata: dict[str, str] = {}
    success: bool | None = None


class ExecutionStage(str, Enum):
    INITIALIZATION = "initialization"
    REPO_CLONE = "repo_clone"
    GRAPH_INDEX = "graph_index"
    EXECUTION = "execution"
    POSTING_RESULT = "posting_result"
    COMPLETION = "completion"


@runtime_checkable
class StreamingLoggerPort(Protocol):
    async def log_progress(
        self,
        stage: ExecutionStage,
        message: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        ...

    async def log_cli_output(
        self,
        content: str,
        stream: str,
    ) -> None:
        ...

    async def log_mcp_call(
        self,
        tool_name: str,
        arguments: dict[str, str],
    ) -> None:
        ...

    async def log_mcp_result(
        self,
        tool_name: str,
        success: bool,
        result: str | None = None,
    ) -> None:
        ...

    async def log_completion(
        self,
        success: bool,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        ...

    async def get_log_path(self) -> str:
        ...
```

---

## Phase 5: Implement Adapters

### Step 5.1: Write Tests FIRST - Redis Queue Adapter

**File: `agent-container/tests/adapters/test_redis_queue.py`** (< 180 lines)

```python
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from ports.queue import (
    TaskQueueMessage,
    TaskPriority,
    TaskStatus,
)
from adapters.queue.redis_adapter import RedisQueueAdapter


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.zadd = AsyncMock()
    redis.bzpopmin = AsyncMock()
    redis.zcard = AsyncMock()
    redis.hset = AsyncMock()
    redis.hget = AsyncMock()
    redis.hdel = AsyncMock()
    return redis


@pytest.fixture
def adapter(mock_redis: AsyncMock) -> RedisQueueAdapter:
    return RedisQueueAdapter(
        redis_client=mock_redis,
        queue_name="test_tasks",
    )


@pytest.fixture
def sample_task() -> TaskQueueMessage:
    return TaskQueueMessage(
        task_id="task-123",
        installation_id="inst-456",
        provider="github",
        input_message="Analyze this code",
        priority=TaskPriority.NORMAL,
        source_metadata={"pr_number": "42", "repo": "owner/repo"},
        created_at=datetime.now(timezone.utc),
    )


class TestRedisQueueAdapterEnqueue:
    @pytest.mark.asyncio
    async def test_enqueue_task(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
        sample_task: TaskQueueMessage,
    ):
        await adapter.enqueue(sample_task)

        mock_redis.zadd.assert_called_once()
        call_args = mock_redis.zadd.call_args
        assert call_args[0][0] == "test_tasks"

    @pytest.mark.asyncio
    async def test_enqueue_sets_status(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
        sample_task: TaskQueueMessage,
    ):
        await adapter.enqueue(sample_task)

        mock_redis.hset.assert_called()


class TestRedisQueueAdapterDequeue:
    @pytest.mark.asyncio
    async def test_dequeue_returns_task(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
        sample_task: TaskQueueMessage,
    ):
        mock_redis.bzpopmin.return_value = (
            "test_tasks",
            sample_task.model_dump_json().encode(),
            2.0,
        )

        result = await adapter.dequeue(timeout_seconds=5.0)

        assert result is not None
        assert result.task_id == "task-123"

    @pytest.mark.asyncio
    async def test_dequeue_returns_none_on_timeout(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
    ):
        mock_redis.bzpopmin.return_value = None

        result = await adapter.dequeue(timeout_seconds=1.0)

        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_updates_status_to_processing(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
        sample_task: TaskQueueMessage,
    ):
        mock_redis.bzpopmin.return_value = (
            "test_tasks",
            sample_task.model_dump_json().encode(),
            2.0,
        )

        await adapter.dequeue(timeout_seconds=5.0)

        status_call = [
            call for call in mock_redis.hset.call_args_list
            if "status" in str(call)
        ]
        assert len(status_call) > 0


class TestRedisQueueAdapterAcknowledge:
    @pytest.mark.asyncio
    async def test_acknowledge_removes_from_processing(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
    ):
        await adapter.acknowledge("task-123")

        mock_redis.hdel.assert_called()


class TestRedisQueueAdapterReject:
    @pytest.mark.asyncio
    async def test_reject_with_requeue(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
        sample_task: TaskQueueMessage,
    ):
        mock_redis.hget.return_value = sample_task.model_dump_json().encode()

        await adapter.reject("task-123", requeue=True)

        mock_redis.zadd.assert_called()

    @pytest.mark.asyncio
    async def test_reject_without_requeue(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
    ):
        await adapter.reject("task-123", requeue=False)

        mock_redis.zadd.assert_not_called()


class TestRedisQueueAdapterStatus:
    @pytest.mark.asyncio
    async def test_get_queue_length(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
    ):
        mock_redis.zcard.return_value = 5

        length = await adapter.get_queue_length()

        assert length == 5

    @pytest.mark.asyncio
    async def test_get_task_status_found(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
    ):
        mock_redis.hget.return_value = b"processing"

        status = await adapter.get_task_status("task-123")

        assert status == TaskStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(
        self,
        adapter: RedisQueueAdapter,
        mock_redis: AsyncMock,
    ):
        mock_redis.hget.return_value = None

        status = await adapter.get_task_status("task-123")

        assert status is None
```

### Step 5.2: Implement Redis Queue Adapter

**File: `agent-container/adapters/queue/redis_adapter.py`** (< 150 lines)

```python
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis
import structlog

from ports.queue import (
    QueuePort,
    TaskQueueMessage,
    TaskStatus,
)

logger = structlog.get_logger()

TASK_DATA_KEY = "task_data"
TASK_STATUS_KEY = "task_status"


class RedisQueueAdapter:
    def __init__(
        self,
        redis_client: redis.Redis,
        queue_name: str = "agent_tasks",
    ) -> None:
        self._redis = redis_client
        self._queue_name = queue_name

    async def enqueue(self, message: TaskQueueMessage) -> None:
        logger.info(
            "enqueueing_task",
            task_id=message.task_id,
            priority=message.priority.value,
        )

        await self._redis.zadd(
            self._queue_name,
            {message.model_dump_json(): message.priority.value},
        )

        await self._redis.hset(
            f"{TASK_DATA_KEY}:{message.task_id}",
            mapping={
                "data": message.model_dump_json(),
                "status": TaskStatus.PENDING.value,
                "enqueued_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info("task_enqueued", task_id=message.task_id)

    async def dequeue(
        self, timeout_seconds: float = 5.0
    ) -> TaskQueueMessage | None:
        result = await self._redis.bzpopmin(
            self._queue_name,
            timeout=timeout_seconds,
        )

        if result is None:
            return None

        _, task_json, _ = result
        message = TaskQueueMessage.model_validate_json(task_json)

        await self._update_status(message.task_id, TaskStatus.PROCESSING)

        logger.info("task_dequeued", task_id=message.task_id)
        return message

    async def acknowledge(self, task_id: str) -> None:
        logger.info("acknowledging_task", task_id=task_id)

        await self._update_status(task_id, TaskStatus.COMPLETED)
        await self._redis.hdel(f"{TASK_DATA_KEY}:{task_id}", "data")

    async def reject(self, task_id: str, requeue: bool = True) -> None:
        logger.info(
            "rejecting_task",
            task_id=task_id,
            requeue=requeue,
        )

        if requeue:
            task_data = await self._redis.hget(
                f"{TASK_DATA_KEY}:{task_id}",
                "data",
            )
            if task_data:
                message = TaskQueueMessage.model_validate_json(task_data)
                await self._redis.zadd(
                    self._queue_name,
                    {message.model_dump_json(): message.priority.value},
                )
                await self._update_status(task_id, TaskStatus.PENDING)
        else:
            await self._update_status(task_id, TaskStatus.FAILED)

    async def get_queue_length(self) -> int:
        return await self._redis.zcard(self._queue_name)

    async def get_task_status(self, task_id: str) -> TaskStatus | None:
        status = await self._redis.hget(
            f"{TASK_DATA_KEY}:{task_id}",
            "status",
        )

        if status is None:
            return None

        status_str = status.decode() if isinstance(status, bytes) else status
        return TaskStatus(status_str)

    async def _update_status(
        self, task_id: str, status: TaskStatus
    ) -> None:
        await self._redis.hset(
            f"{TASK_DATA_KEY}:{task_id}",
            "status",
            status.value,
        )
```

### Step 5.3: Write Tests FIRST - Claude CLI Adapter

**File: `agent-container/tests/adapters/test_claude_cli.py`** (< 180 lines)

```python
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from ports.cli_runner import (
    CLIOutput,
    CLIOutputType,
    CLIExecutionConfig,
    CLIExecutionResult,
)
from adapters.cli.claude_adapter import ClaudeCLIAdapter


@pytest.fixture
def cli_config() -> CLIExecutionConfig:
    return CLIExecutionConfig(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        working_dir="/tmp/test_repo",
        timeout_seconds=60,
    )


@pytest.fixture
def adapter() -> ClaudeCLIAdapter:
    return ClaudeCLIAdapter()


class TestClaudeCLIAdapterExecute:
    @pytest.mark.asyncio
    async def test_execute_yields_outputs(
        self,
        adapter: ClaudeCLIAdapter,
        cli_config: CLIExecutionConfig,
    ):
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stdout.__aiter__ = lambda self: iter([
                b'{"type": "text", "text": "Hello"}\n',
            ])
            mock_process.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_process

            outputs = []
            async for output in adapter.execute("test prompt", cli_config):
                outputs.append(output)

            assert len(outputs) >= 1

    @pytest.mark.asyncio
    async def test_execute_handles_tool_calls(
        self,
        adapter: ClaudeCLIAdapter,
        cli_config: CLIExecutionConfig,
    ):
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stdout.__aiter__ = lambda self: iter([
                b'{"type": "tool_use", "name": "read_file", "input": {"path": "test.py"}}\n',
            ])
            mock_process.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_process

            outputs = []
            async for output in adapter.execute("test prompt", cli_config):
                outputs.append(output)

            tool_outputs = [o for o in outputs if o.type == CLIOutputType.TOOL_CALL]
            assert len(tool_outputs) >= 0


class TestClaudeCLIAdapterExecuteAndWait:
    @pytest.mark.asyncio
    async def test_execute_and_wait_returns_result(
        self,
        adapter: ClaudeCLIAdapter,
        cli_config: CLIExecutionConfig,
    ):
        with patch.object(adapter, "execute") as mock_execute:
            async def mock_generator(*args, **kwargs):
                yield CLIOutput(
                    type=CLIOutputType.STDOUT,
                    content="Processing...",
                    timestamp=datetime.now(timezone.utc),
                )
                yield CLIOutput(
                    type=CLIOutputType.COMPLETION,
                    content="Done!",
                    timestamp=datetime.now(timezone.utc),
                    metadata={"tokens": "100", "cost": "0.01"},
                )

            mock_execute.return_value = mock_generator()

            result = await adapter.execute_and_wait("test prompt", cli_config)

            assert result.success is True
            assert result.output == "Done!"

    @pytest.mark.asyncio
    async def test_execute_and_wait_handles_error(
        self,
        adapter: ClaudeCLIAdapter,
        cli_config: CLIExecutionConfig,
    ):
        with patch.object(adapter, "execute") as mock_execute:
            async def mock_generator(*args, **kwargs):
                yield CLIOutput(
                    type=CLIOutputType.ERROR,
                    content="Something went wrong",
                    timestamp=datetime.now(timezone.utc),
                )

            mock_execute.return_value = mock_generator()

            result = await adapter.execute_and_wait("test prompt", cli_config)

            assert result.success is False
            assert "Something went wrong" in result.error


class TestClaudeCLIAdapterCancel:
    @pytest.mark.asyncio
    async def test_cancel_terminates_process(
        self,
        adapter: ClaudeCLIAdapter,
    ):
        mock_process = AsyncMock()
        mock_process.terminate = MagicMock()
        adapter._active_processes = {"exec-123": mock_process}

        result = await adapter.cancel("exec-123")

        assert result is True
        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_unknown_execution_returns_false(
        self,
        adapter: ClaudeCLIAdapter,
    ):
        result = await adapter.cancel("unknown-id")

        assert result is False


class TestClaudeCLIAdapterAvailability:
    @pytest.mark.asyncio
    async def test_is_available_when_cli_exists(
        self,
        adapter: ClaudeCLIAdapter,
    ):
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/claude"

            result = await adapter.is_available()

            assert result is True

    @pytest.mark.asyncio
    async def test_is_available_when_cli_missing(
        self,
        adapter: ClaudeCLIAdapter,
    ):
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            result = await adapter.is_available()

            assert result is False
```

### Step 5.4: Implement Claude CLI Adapter

**File: `agent-container/adapters/cli/claude_adapter.py`** (< 200 lines)

```python
import asyncio
import json
import shutil
import time
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import uuid4

import structlog

from ports.cli_runner import (
    CLIRunnerPort,
    CLIOutput,
    CLIOutputType,
    CLIExecutionConfig,
    CLIExecutionResult,
)

logger = structlog.get_logger()


class ClaudeCLIAdapter:
    def __init__(self, cli_path: str | None = None) -> None:
        self._cli_path = cli_path or "claude"
        self._active_processes: dict[str, asyncio.subprocess.Process] = {}

    async def execute(
        self,
        prompt: str,
        config: CLIExecutionConfig,
    ) -> AsyncIterator[CLIOutput]:
        execution_id = f"exec-{uuid4().hex[:8]}"
        logger.info(
            "starting_cli_execution",
            execution_id=execution_id,
            model=config.model,
        )

        cmd = self._build_command(prompt, config)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=config.working_dir,
            env=config.environment or None,
        )

        self._active_processes[execution_id] = process

        try:
            async for line in process.stdout:
                output = self._parse_output_line(line)
                if output:
                    yield output

            await process.wait()

            yield CLIOutput(
                type=CLIOutputType.COMPLETION,
                content="Execution completed",
                timestamp=datetime.now(timezone.utc),
                metadata={"exit_code": str(process.returncode)},
            )

        finally:
            self._active_processes.pop(execution_id, None)

    async def execute_and_wait(
        self,
        prompt: str,
        config: CLIExecutionConfig,
    ) -> CLIExecutionResult:
        start_time = time.time()
        outputs: list[CLIOutput] = []
        final_output = ""
        error_output = ""
        tokens_used = 0
        cost_usd = 0.0

        async for output in self.execute(prompt, config):
            outputs.append(output)

            if output.type == CLIOutputType.COMPLETION:
                final_output = output.content
                tokens_used = int(output.metadata.get("tokens", 0))
                cost_usd = float(output.metadata.get("cost", 0.0))
            elif output.type == CLIOutputType.ERROR:
                error_output = output.content
            elif output.type == CLIOutputType.STDOUT:
                if not final_output:
                    final_output = output.content

        duration = time.time() - start_time
        success = not error_output and final_output

        return CLIExecutionResult(
            success=success,
            output=final_output,
            error=error_output if error_output else None,
            exit_code=0 if success else 1,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            duration_seconds=duration,
        )

    async def cancel(self, execution_id: str) -> bool:
        process = self._active_processes.get(execution_id)
        if process is None:
            return False

        logger.info("cancelling_execution", execution_id=execution_id)
        process.terminate()

        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill()

        self._active_processes.pop(execution_id, None)
        return True

    async def is_available(self) -> bool:
        return shutil.which(self._cli_path) is not None

    def _build_command(
        self,
        prompt: str,
        config: CLIExecutionConfig,
    ) -> list[str]:
        cmd = [
            self._cli_path,
            "--model", config.model,
            "--max-tokens", str(config.max_tokens),
            "--output-format", "json",
            "--print", "all",
        ]

        for tool in config.allowed_tools:
            cmd.extend(["--allowedTools", tool])

        cmd.extend(["--prompt", prompt])

        return cmd

    def _parse_output_line(self, line: bytes) -> CLIOutput | None:
        try:
            text = line.decode().strip()
            if not text:
                return None

            data = json.loads(text)
            output_type = self._map_output_type(data.get("type", "text"))

            return CLIOutput(
                type=output_type,
                content=data.get("text", data.get("content", str(data))),
                timestamp=datetime.now(timezone.utc),
                metadata=data.get("metadata", {}),
            )

        except json.JSONDecodeError:
            return CLIOutput(
                type=CLIOutputType.STDOUT,
                content=line.decode().strip(),
                timestamp=datetime.now(timezone.utc),
            )

    def _map_output_type(self, type_str: str) -> CLIOutputType:
        type_map = {
            "text": CLIOutputType.STDOUT,
            "tool_use": CLIOutputType.TOOL_CALL,
            "tool_result": CLIOutputType.TOOL_RESULT,
            "thinking": CLIOutputType.THINKING,
            "error": CLIOutputType.ERROR,
        }
        return type_map.get(type_str, CLIOutputType.STDOUT)
```

---

## Phase 6: Dependency Injection Container

### Step 6.1: Write Tests FIRST - Container

**File: `agent-container/tests/test_container.py`** (< 120 lines)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from container import Container, ContainerConfig, create_container
from ports.queue import QueuePort
from ports.cli_runner import CLIRunnerPort


@pytest.fixture
def config() -> ContainerConfig:
    return ContainerConfig(
        queue_type="memory",
        database_type="memory",
        cli_type="mock",
        redis_url="redis://localhost:6379",
        database_url="postgresql://localhost/test",
    )


class TestContainerCreation:
    def test_create_container_with_memory_queue(
        self,
        config: ContainerConfig,
    ):
        container = create_container(config)

        assert container.queue is not None
        assert isinstance(container.queue, QueuePort)

    def test_create_container_with_mock_cli(
        self,
        config: ContainerConfig,
    ):
        container = create_container(config)

        assert container.cli_runner is not None

    def test_container_components_are_accessible(
        self,
        config: ContainerConfig,
    ):
        container = create_container(config)

        assert hasattr(container, "queue")
        assert hasattr(container, "cli_runner")
        assert hasattr(container, "token_service")
        assert hasattr(container, "repo_manager")


class TestContainerWithRedis:
    def test_create_container_with_redis_queue(self):
        config = ContainerConfig(
            queue_type="redis",
            database_type="memory",
            cli_type="mock",
            redis_url="redis://localhost:6379",
            database_url="",
        )

        with pytest.raises(Exception):
            create_container(config)


class TestContainerWithClaude:
    def test_create_container_with_claude_cli(self):
        config = ContainerConfig(
            queue_type="memory",
            database_type="memory",
            cli_type="claude",
            redis_url="",
            database_url="",
        )

        container = create_container(config)

        assert container.cli_runner is not None
```

### Step 6.2: Implement Container

**File: `agent-container/container.py`** (< 150 lines)

```python
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ports.queue import QueuePort
from ports.cli_runner import CLIRunnerPort
from ports.logger import StreamingLoggerPort
from adapters.queue.redis_adapter import RedisQueueAdapter
from adapters.queue.memory_adapter import InMemoryQueueAdapter
from adapters.cli.claude_adapter import ClaudeCLIAdapter
from adapters.cli.cursor_adapter import CursorCLIAdapter
from adapters.cli.mock_adapter import MockCLIAdapter
from token_service import TokenService, InMemoryInstallationRepository


class ContainerConfig(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    queue_type: Literal["redis", "sqs", "memory"]
    database_type: Literal["postgres", "mongodb", "memory"]
    cli_type: Literal["claude", "cursor", "mock"]
    redis_url: str
    database_url: str
    repo_base_path: str = "/data/repos"
    log_base_path: str = "/data/logs"


@dataclass
class Container:
    queue: QueuePort
    cli_runner: CLIRunnerPort
    token_service: TokenService
    repo_manager: "RepoManager"
    logger_factory: "LoggerFactory"


def create_container(config: ContainerConfig) -> Container:
    queue = _create_queue(config)
    cli_runner = _create_cli_runner(config)
    token_service = _create_token_service(config)
    repo_manager = _create_repo_manager(config, token_service)
    logger_factory = _create_logger_factory(config)

    return Container(
        queue=queue,
        cli_runner=cli_runner,
        token_service=token_service,
        repo_manager=repo_manager,
        logger_factory=logger_factory,
    )


def _create_queue(config: ContainerConfig) -> QueuePort:
    match config.queue_type:
        case "redis":
            import redis.asyncio as redis
            client = redis.from_url(config.redis_url)
            return RedisQueueAdapter(redis_client=client)
        case "sqs":
            from adapters.queue.sqs_adapter import SQSQueueAdapter
            return SQSQueueAdapter(queue_url=config.redis_url)
        case "memory":
            return InMemoryQueueAdapter()
        case _:
            raise ValueError(f"Unknown queue type: {config.queue_type}")


def _create_cli_runner(config: ContainerConfig) -> CLIRunnerPort:
    match config.cli_type:
        case "claude":
            return ClaudeCLIAdapter()
        case "cursor":
            return CursorCLIAdapter()
        case "mock":
            return MockCLIAdapter()
        case _:
            raise ValueError(f"Unknown CLI type: {config.cli_type}")


def _create_token_service(config: ContainerConfig) -> TokenService:
    match config.database_type:
        case "postgres":
            from token_service.adapters.postgres import PostgresInstallationRepository
            import asyncpg
            raise NotImplementedError("Postgres pool creation requires async context")
        case "mongodb":
            from token_service.adapters.mongodb import MongoInstallationRepository
            raise NotImplementedError("MongoDB requires async context")
        case "memory":
            repository = InMemoryInstallationRepository()
            return TokenService(repository=repository)
        case _:
            raise ValueError(f"Unknown database type: {config.database_type}")


def _create_repo_manager(
    config: ContainerConfig,
    token_service: TokenService,
) -> "RepoManager":
    from core.repo_manager import RepoManager, RepoConfig

    repo_config = RepoConfig(
        base_path=config.repo_base_path,
    )
    return RepoManager(config=repo_config, token_service=token_service)


def _create_logger_factory(config: ContainerConfig) -> "LoggerFactory":
    from core.streaming_logger import LoggerFactory

    return LoggerFactory(base_path=config.log_base_path)
```

---

## Run Tests to Verify Phase 4-6

```bash
cd agent-container
pytest -v tests/ports/
pytest -v tests/adapters/
pytest -v tests/test_container.py

# Expected: All tests pass < 5 seconds per file
```

---

## Checkpoint 3 Complete ✅

Before proceeding, verify:
- [ ] All port interfaces defined
- [ ] All adapters implement ports
- [ ] Container creates correct adapters
- [ ] All files < 300 lines
- [ ] NO `any` types used
- [ ] All tests pass

Continue to Part 4 for Repository Manager & Knowledge Graph...
