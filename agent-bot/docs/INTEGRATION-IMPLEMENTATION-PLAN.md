# Claude-Code-Agent Integration into Agent-Bot

## Complete Implementation Plan with TDD Approach

> **Goal**: Integrate `claude-code-agent` business logic into `agent-bot` containerized architecture with full test coverage, strict typing, and modular code.

---

## Executive Summary

This document provides a step-by-step implementation plan for migrating the production-tested `claude-code-agent` system into the containerized `agent-bot` microservices architecture. The implementation follows strict TDD (Test-Driven Development) methodology:

**TDD Cycle**: `Write Test → Run (Fail) → Implement → Run (Pass) → Refactor`

---

## Architecture Overview

### Target Architecture: 14 Containers

```
┌─────────────────────────────────────────────────────────────────────┐
│                     External Services                                │
│              (GitHub, Jira, Slack, Sentry)                          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    API Gateway :8000          │
              │    (Webhook Reception)        │
              └───────────────────────────────┘
                 │                    │
                 ▼                    ▼
          ┌──────────┐       ┌────────────────┐
          │  Redis   │       │ Knowledge      │
          │  :6379   │       │ Graph :4000    │
          └──────────┘       └────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                Agent Engine :8080-8089 (Scalable)                    │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  agent-engine-package/                                          │ │
│  │  ├── core/ (CLI providers, worker, queue)                       │ │
│  │  ├── agents/ (13 specialized agents)                            │ │
│  │  ├── skills/ (reusable capabilities)                            │ │
│  │  └── memory/ (self-improvement)                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  mcp.json → SSE connections to MCP servers                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                 │ (SSE Connections)
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│              MCP Servers (4 Containers)                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                   │
│  │ GitHub  │ │  Jira   │ │  Slack  │ │ Sentry  │                   │
│  │  :9001  │ │  :9002  │ │  :9003  │ │  :9004  │                   │
│  │(Official)│ │(FastMCP)│ │(FastMCP)│ │(FastMCP)│                   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘                   │
└──────────────────────────────────────────────────────────────────────┘
                 │ (HTTP API Calls)
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│              API Services (4 Containers)                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                   │
│  │ GitHub  │ │  Jira   │ │  Slack  │ │ Sentry  │                   │
│  │  :3001  │ │  :3002  │ │  :3003  │ │  :3004  │                   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘                   │
└──────────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Dashboard Layer                                         │
│  ┌───────────────────────┐ ┌────────────────────────┐               │
│  │ Internal Dashboard    │ │ External Dashboard     │               │
│  │ API :5000             │ │ (React) :3002          │               │
│  └───────────────────────┘ └────────────────────────┘               │
└──────────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Data Layer                                              │
│  ┌───────────────────────┐ ┌────────────────────────┐               │
│  │   PostgreSQL :5432    │ │     Redis :6379        │               │
│  └───────────────────────┘ └────────────────────────┘               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Principles

### 1. Agent Engine as Package

The agent-engine will be a **self-contained Python package** that can be loaded into any container:

```
agent-engine-package/
├── pyproject.toml
├── agent_engine/
│   ├── __init__.py
│   ├── core/
│   │   ├── cli/
│   │   │   ├── base.py          # Protocol/Interface
│   │   │   ├── executor.py      # Main executor
│   │   │   └── providers/
│   │   │       ├── claude/      # Claude CLI provider
│   │   │       └── cursor/      # Cursor CLI provider
│   │   ├── worker.py            # Task worker
│   │   ├── queue_manager.py     # Redis queue
│   │   └── config.py            # Settings
│   ├── agents/                  # 13 specialized agents
│   ├── skills/                  # Reusable capabilities
│   └── memory/                  # Self-improvement
└── tests/
```

### 2. CLI Provider Architecture

Support multiple CLI providers (Claude Code, Cursor) with headless streaming:

```python
from typing import Protocol, runtime_checkable
from dataclasses import dataclass
import asyncio

@dataclass(frozen=True)
class CLIResult:
    success: bool
    output: str
    clean_output: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    error: str | None = None

@runtime_checkable
class CLIProvider(Protocol):
    async def run(
        self,
        prompt: str,
        working_dir: Path,
        output_queue: asyncio.Queue[str | None],
        task_id: str,
        timeout_seconds: int,
        model: str | None,
        allowed_tools: str | None,
    ) -> CLIResult:
        ...
```

### 3. Strict Type Safety

- NO `any` types
- Pydantic models with `ConfigDict(strict=True)`
- Explicit return types
- Dataclasses for value objects

### 4. No Comments Policy

- Self-explanatory code through naming
- Docstrings only for public APIs
- Extract complex logic to named functions

---

## Implementation Phases

### Phase 1: Foundation & Infrastructure (Week 1-2)

**Goal**: Set up project structure, base classes, and infrastructure containers.

#### Step 1.1: Project Structure Setup

**Test First (test_project_structure.py)**:
```python
import pytest
from pathlib import Path

def test_agent_engine_package_exists():
    package_dir = Path("agent-bot/agent-engine-package")
    assert package_dir.exists()
    assert (package_dir / "pyproject.toml").exists()
    assert (package_dir / "agent_engine" / "__init__.py").exists()

def test_core_modules_exist():
    core_dir = Path("agent-bot/agent-engine-package/agent_engine/core")
    assert (core_dir / "cli" / "base.py").exists()
    assert (core_dir / "cli" / "executor.py").exists()
    assert (core_dir / "worker.py").exists()
    assert (core_dir / "queue_manager.py").exists()
    assert (core_dir / "config.py").exists()

def test_provider_directories_exist():
    providers_dir = Path("agent-bot/agent-engine-package/agent_engine/core/cli/providers")
    assert (providers_dir / "claude").exists()
    assert (providers_dir / "cursor").exists()
```

**Implementation**:
1. Create directory structure
2. Create `pyproject.toml` with dependencies
3. Create `__init__.py` files
4. Create empty module files

**Files to Create**:
```
agent-bot/
├── agent-engine-package/
│   ├── pyproject.toml
│   ├── agent_engine/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── cli/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── executor.py
│   │   │   │   └── providers/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── claude/
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── runner.py
│   │   │   │       │   └── config.py
│   │   │   │       └── cursor/
│   │   │   │           ├── __init__.py
│   │   │   │           ├── runner.py
│   │   │   │           └── config.py
│   │   │   ├── worker.py
│   │   │   ├── queue_manager.py
│   │   │   └── config.py
│   │   ├── agents/
│   │   │   └── __init__.py
│   │   ├── skills/
│   │   │   └── __init__.py
│   │   └── memory/
│   │       └── __init__.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       └── unit/
│           └── __init__.py
```

#### Step 1.2: Base CLI Provider Interface

**Test First (test_cli_base.py)**:
```python
import pytest
import asyncio
from agent_engine.core.cli.base import CLIResult, CLIProvider

def test_cli_result_immutable():
    result = CLIResult(
        success=True,
        output="test",
        clean_output="test",
        cost_usd=0.01,
        input_tokens=100,
        output_tokens=50,
        error=None
    )
    with pytest.raises(AttributeError):
        result.success = False

def test_cli_result_fields():
    result = CLIResult(
        success=True,
        output="full output",
        clean_output="clean",
        cost_usd=0.0123,
        input_tokens=100,
        output_tokens=50,
        error=None
    )
    assert result.success is True
    assert result.output == "full output"
    assert result.clean_output == "clean"
    assert result.cost_usd == 0.0123
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.error is None

def test_cli_provider_protocol():
    assert hasattr(CLIProvider, "run")
```

**Implementation (base.py)**:
```python
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable
import asyncio

@dataclass(frozen=True)
class CLIResult:
    success: bool
    output: str
    clean_output: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    error: str | None = None

@runtime_checkable
class CLIProvider(Protocol):
    async def run(
        self,
        prompt: str,
        working_dir: Path,
        output_queue: asyncio.Queue[str | None],
        task_id: str,
        timeout_seconds: int = 3600,
        model: str | None = None,
        allowed_tools: str | None = None,
    ) -> CLIResult:
        ...
```

#### Step 1.3: Configuration Management

**Test First (test_config.py)**:
```python
import pytest
from agent_engine.core.config import Settings, CLIProviderType

def test_settings_default_values():
    settings = Settings()
    assert settings.max_concurrent_tasks == 5
    assert settings.task_timeout_seconds == 3600
    assert settings.cli_provider == CLIProviderType.CLAUDE

def test_settings_cli_provider_enum():
    assert CLIProviderType.CLAUDE.value == "claude"
    assert CLIProviderType.CURSOR.value == "cursor"

def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("CLI_PROVIDER", "cursor")
    monkeypatch.setenv("MAX_CONCURRENT_TASKS", "10")
    settings = Settings()
    assert settings.cli_provider == CLIProviderType.CURSOR
    assert settings.max_concurrent_tasks == 10

def test_settings_model_selection():
    settings = Settings()
    assert "opus" in settings.get_model_for_agent("planning")
    assert "sonnet" in settings.get_model_for_agent("executor")
```

**Implementation (config.py)**:
```python
from enum import Enum
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class CLIProviderType(str, Enum):
    CLAUDE = "claude"
    CURSOR = "cursor"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    machine_id: str = "agent-engine-001"
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 3600

    cli_provider: CLIProviderType = CLIProviderType.CLAUDE

    redis_url: str = "redis://redis:6379/0"
    database_url: str = "postgresql+asyncpg://agent:agent@postgres:5432/agent_system"

    log_level: str = "INFO"

    claude_model_planning: str = "claude-opus-4-5-20251101"
    claude_model_brain: str = "claude-opus-4-5-20251101"
    claude_model_executor: str = "claude-sonnet-4-5-20250929"
    claude_default_model: str = "claude-sonnet-4-5-20250929"

    default_allowed_tools: str = "Read,Edit,Bash,Glob,Grep,Write"

    def get_model_for_agent(self, agent_type: str) -> str:
        agent_lower = agent_type.lower()
        if agent_lower == "planning":
            return self.claude_model_planning
        elif agent_lower == "executor":
            return self.claude_model_executor
        elif agent_lower == "brain":
            return self.claude_model_brain
        return self.claude_default_model

settings = Settings()
```

#### Step 1.4: Docker Infrastructure

**Test First (test_docker_infrastructure.py)**:
```python
import pytest
from pathlib import Path
import yaml

def test_docker_compose_exists():
    compose_file = Path("agent-bot/docker-compose.yml")
    assert compose_file.exists()

def test_docker_compose_services():
    compose_file = Path("agent-bot/docker-compose.yml")
    with open(compose_file) as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    assert "redis" in services
    assert "postgres" in services
    assert "api-gateway" in services
    assert "agent-engine" in services

def test_agent_engine_dockerfile_exists():
    dockerfile = Path("agent-bot/agent-engine/Dockerfile")
    assert dockerfile.exists()
```

**Implementation**: Create docker-compose.yml and Dockerfiles.

---

### Phase 2: CLI Provider Implementation (Week 2-3)

**Goal**: Implement Claude and Cursor CLI providers with headless streaming.

#### Step 2.1: Sensitive Content Sanitization

**Test First (test_sanitization.py)**:
```python
import pytest
from agent_engine.core.cli.sanitization import sanitize_sensitive_content, contains_sensitive_data

def test_sanitize_github_token():
    content = "GITHUB_TOKEN=ghp_abc123xyz"
    sanitized = sanitize_sensitive_content(content)
    assert "ghp_abc123xyz" not in sanitized
    assert "***REDACTED***" in sanitized

def test_sanitize_authorization_header():
    content = "Authorization: Bearer sk-1234567890"
    sanitized = sanitize_sensitive_content(content)
    assert "sk-1234567890" not in sanitized

def test_contains_sensitive_data():
    assert contains_sensitive_data("GITHUB_TOKEN=abc")
    assert contains_sensitive_data("password: secret123")
    assert not contains_sensitive_data("hello world")

def test_sanitize_handles_list_input():
    content = ["line1", "GITHUB_TOKEN=secret", "line3"]
    sanitized = sanitize_sensitive_content(content)
    assert "secret" not in sanitized
```

**Implementation (sanitization.py)**:
```python
import re

SENSITIVE_PATTERNS: list[tuple[str, str] | tuple[str, str, int]] = [
    (
        r"(JIRA_API_TOKEN|JIRA_EMAIL|GITHUB_TOKEN|SLACK_BOT_TOKEN|SLACK_WEBHOOK_SECRET|GITHUB_WEBHOOK_SECRET|JIRA_WEBHOOK_SECRET)\s*=\s*([^\s\n]+)",
        r"\1=***REDACTED***",
    ),
    (
        r"(password|passwd|pwd|token|secret|api_key|apikey|access_token|refresh_token)\s*[:=]\s*([^\s\n]+)",
        r"\1=***REDACTED***",
        re.IGNORECASE,
    ),
    (r"(Authorization:\s*Bearer\s+)([^\s\n]+)", r"\1***REDACTED***"),
    (r"(Authorization:\s*Basic\s+)([^\s\n]+)", r"\1***REDACTED***"),
]

def sanitize_sensitive_content(content: str | list[str]) -> str:
    if not content:
        return ""

    if isinstance(content, list):
        content = "\n".join(str(item) for item in content)
    elif not isinstance(content, str):
        content = str(content)

    sanitized = content
    for pattern in SENSITIVE_PATTERNS:
        if len(pattern) == 2:
            sanitized = re.sub(pattern[0], pattern[1], sanitized)
        else:
            sanitized = re.sub(pattern[0], pattern[1], sanitized, flags=pattern[2])

    return sanitized

def contains_sensitive_data(content: str) -> bool:
    if not content:
        return False

    indicators = [
        r"JIRA_API_TOKEN\s*=",
        r"GITHUB_TOKEN\s*=",
        r"SLACK_BOT_TOKEN\s*=",
        r"password\s*[:=]",
        r"token\s*[:=]",
        r"secret\s*[:=]",
        r"Authorization:\s*(Bearer|Basic)",
    ]

    content_str = str(content) if not isinstance(content, str) else content

    for pattern in indicators:
        if re.search(pattern, content_str, re.IGNORECASE):
            return True

    return False
```

#### Step 2.2: Claude CLI Provider

**Test First (test_claude_provider.py)**:
```python
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from agent_engine.core.cli.providers.claude.runner import ClaudeCLIRunner
from agent_engine.core.cli.base import CLIResult, CLIProvider

def test_claude_runner_implements_protocol():
    runner = ClaudeCLIRunner()
    assert isinstance(runner, CLIProvider)

@pytest.mark.asyncio
async def test_claude_runner_builds_correct_command():
    runner = ClaudeCLIRunner()

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.stdout.__aiter__ = AsyncMock(return_value=iter([]))
        mock_process.stderr.__aiter__ = AsyncMock(return_value=iter([]))
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        output_queue = asyncio.Queue()
        await runner.run(
            prompt="test prompt",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-123",
            timeout_seconds=60,
            model="claude-sonnet-4-5-20250929",
        )

        call_args = mock_exec.call_args
        cmd = call_args[0]
        assert "claude" in cmd
        assert "-p" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--dangerously-skip-permissions" in cmd

@pytest.mark.asyncio
async def test_claude_runner_handles_timeout():
    runner = ClaudeCLIRunner()

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()
        mock_exec.return_value = mock_process

        async def slow_read():
            await asyncio.sleep(10)
            yield b""

        mock_process.stdout.__aiter__ = slow_read
        mock_process.stderr.__aiter__ = AsyncMock(return_value=iter([]))

        output_queue = asyncio.Queue()
        result = await runner.run(
            prompt="test",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-123",
            timeout_seconds=1,
        )

        assert result.success is False
        assert "Timeout" in (result.error or "")

@pytest.mark.asyncio
async def test_claude_runner_streams_output():
    runner = ClaudeCLIRunner()

    json_lines = [
        b'{"type": "init", "content": "Starting..."}\n',
        b'{"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hello"}}}\n',
        b'{"type": "result", "total_cost_usd": 0.01, "usage": {"input_tokens": 100, "output_tokens": 50}}\n',
    ]

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=0)

        async def mock_stdout():
            for line in json_lines:
                yield line

        async def mock_stderr():
            return
            yield

        mock_process.stdout = mock_stdout()
        mock_process.stderr = mock_stderr()
        mock_exec.return_value = mock_process

        output_queue = asyncio.Queue()
        result = await runner.run(
            prompt="test",
            working_dir=Path("/tmp"),
            output_queue=output_queue,
            task_id="test-123",
        )

        assert result.success is True
        assert result.cost_usd == 0.01
        assert result.input_tokens == 100
        assert result.output_tokens == 50
```

**Implementation (providers/claude/runner.py)**:
Port the existing `ClaudeCLIRunner` from `claude-code-agent/core/cli/claude.py` with:
- Type annotations
- No comments
- Modular helper functions

#### Step 2.3: Cursor CLI Provider

**Test First (test_cursor_provider.py)**:
```python
import pytest
import asyncio
from pathlib import Path
from agent_engine.core.cli.providers.cursor.runner import CursorCLIRunner
from agent_engine.core.cli.base import CLIProvider

def test_cursor_runner_implements_protocol():
    runner = CursorCLIRunner()
    assert isinstance(runner, CLIProvider)

@pytest.mark.asyncio
async def test_cursor_runner_uses_correct_command():
    runner = CursorCLIRunner()

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Similar setup as Claude tests
        ...

        call_args = mock_exec.call_args
        cmd = call_args[0]
        assert "cursor" in cmd[0]
```

**Implementation (providers/cursor/runner.py)**:
```python
import asyncio
import json
import os
from pathlib import Path
import structlog
from agent_engine.core.cli.base import CLIResult
from agent_engine.core.cli.sanitization import sanitize_sensitive_content

logger = structlog.get_logger()

class CursorCLIRunner:
    async def run(
        self,
        prompt: str,
        working_dir: Path,
        output_queue: asyncio.Queue[str | None],
        task_id: str = "",
        timeout_seconds: int = 3600,
        model: str | None = None,
        allowed_tools: str | None = None,
    ) -> CLIResult:
        cmd = self._build_command(prompt, model)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(working_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                **os.environ,
                "CURSOR_TASK_ID": task_id,
            },
        )

        # Similar streaming logic as Claude provider
        # Adapted for Cursor CLI output format
        ...

    def _build_command(self, prompt: str, model: str | None) -> list[str]:
        cmd = [
            "cursor",
            "--headless",
            "--output-format", "json-stream",
        ]
        if model:
            cmd.extend(["--model", model])
        cmd.extend(["--", prompt])
        return cmd
```

#### Step 2.4: CLI Executor Factory

**Test First (test_executor.py)**:
```python
import pytest
from agent_engine.core.cli.executor import CLIExecutor
from agent_engine.core.cli.providers.claude.runner import ClaudeCLIRunner
from agent_engine.core.cli.providers.cursor.runner import CursorCLIRunner
from agent_engine.core.config import CLIProviderType

def test_executor_loads_claude_provider():
    executor = CLIExecutor(provider_type=CLIProviderType.CLAUDE)
    assert isinstance(executor.provider, ClaudeCLIRunner)

def test_executor_loads_cursor_provider():
    executor = CLIExecutor(provider_type=CLIProviderType.CURSOR)
    assert isinstance(executor.provider, CursorCLIRunner)

def test_executor_default_provider():
    executor = CLIExecutor()
    assert executor.provider is not None

@pytest.mark.asyncio
async def test_executor_delegates_to_provider():
    executor = CLIExecutor(provider_type=CLIProviderType.CLAUDE)

    with patch.object(executor.provider, "run") as mock_run:
        mock_run.return_value = CLIResult(
            success=True, output="ok", clean_output="ok",
            cost_usd=0.01, input_tokens=100, output_tokens=50
        )

        result = await executor.execute(
            prompt="test",
            working_dir=Path("/tmp"),
            task_id="test-123",
        )

        assert mock_run.called
        assert result.success is True
```

**Implementation (executor.py)**:
```python
import asyncio
from pathlib import Path
from agent_engine.core.cli.base import CLIResult, CLIProvider
from agent_engine.core.config import settings, CLIProviderType

class CLIExecutor:
    def __init__(self, provider_type: CLIProviderType | None = None):
        self.provider_type = provider_type or settings.cli_provider
        self.provider = self._load_provider()

    def _load_provider(self) -> CLIProvider:
        if self.provider_type == CLIProviderType.CLAUDE:
            from agent_engine.core.cli.providers.claude.runner import ClaudeCLIRunner
            return ClaudeCLIRunner()
        elif self.provider_type == CLIProviderType.CURSOR:
            from agent_engine.core.cli.providers.cursor.runner import CursorCLIRunner
            return CursorCLIRunner()
        raise ValueError(f"Unknown provider: {self.provider_type}")

    async def execute(
        self,
        prompt: str,
        working_dir: Path,
        task_id: str,
        timeout_seconds: int = 3600,
        model: str | None = None,
        allowed_tools: str | None = None,
    ) -> CLIResult:
        output_queue: asyncio.Queue[str | None] = asyncio.Queue()

        return await self.provider.run(
            prompt=prompt,
            working_dir=working_dir,
            output_queue=output_queue,
            task_id=task_id,
            timeout_seconds=timeout_seconds,
            model=model,
            allowed_tools=allowed_tools,
        )
```

---

### Phase 3: Queue & Worker System (Week 3-4)

**Goal**: Implement Redis queue management and task worker.

#### Step 3.1: Queue Manager

**Test First (test_queue_manager.py)**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from agent_engine.core.queue_manager import QueueManager, TaskStatus

@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    return redis

@pytest.mark.asyncio
async def test_push_task(mock_redis):
    manager = QueueManager(redis_client=mock_redis)
    await manager.push_task("task-123")
    mock_redis.lpush.assert_called_once()

@pytest.mark.asyncio
async def test_pop_task(mock_redis):
    mock_redis.brpop.return_value = (b"tasks", b"task-123")
    manager = QueueManager(redis_client=mock_redis)
    task_id = await manager.pop_task(timeout=5)
    assert task_id == "task-123"

@pytest.mark.asyncio
async def test_pop_task_timeout(mock_redis):
    mock_redis.brpop.return_value = None
    manager = QueueManager(redis_client=mock_redis)
    task_id = await manager.pop_task(timeout=1)
    assert task_id is None

@pytest.mark.asyncio
async def test_set_task_status(mock_redis):
    manager = QueueManager(redis_client=mock_redis)
    await manager.set_task_status("task-123", TaskStatus.RUNNING)
    mock_redis.set.assert_called()

@pytest.mark.asyncio
async def test_get_task_status(mock_redis):
    mock_redis.get.return_value = b"running"
    manager = QueueManager(redis_client=mock_redis)
    status = await manager.get_task_status("task-123")
    assert status == TaskStatus.RUNNING

@pytest.mark.asyncio
async def test_append_output(mock_redis):
    manager = QueueManager(redis_client=mock_redis)
    await manager.append_output("task-123", "chunk of output")
    mock_redis.append.assert_called()
```

**Implementation (queue_manager.py)**:
```python
from enum import Enum
from typing import Protocol
import redis.asyncio as redis

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class QueueManager:
    TASK_QUEUE_KEY = "agent:tasks:queue"
    TASK_STATUS_PREFIX = "agent:task:status:"
    TASK_OUTPUT_PREFIX = "agent:task:output:"

    def __init__(self, redis_client: redis.Redis | None = None, redis_url: str | None = None):
        if redis_client:
            self._client = redis_client
        elif redis_url:
            self._client = redis.from_url(redis_url)
        else:
            from agent_engine.core.config import settings
            self._client = redis.from_url(settings.redis_url)

    async def push_task(self, task_id: str) -> None:
        await self._client.lpush(self.TASK_QUEUE_KEY, task_id)

    async def pop_task(self, timeout: int = 5) -> str | None:
        result = await self._client.brpop(self.TASK_QUEUE_KEY, timeout=timeout)
        if result:
            return result[1].decode()
        return None

    async def set_task_status(self, task_id: str, status: TaskStatus) -> None:
        key = f"{self.TASK_STATUS_PREFIX}{task_id}"
        await self._client.set(key, status.value)

    async def get_task_status(self, task_id: str) -> TaskStatus | None:
        key = f"{self.TASK_STATUS_PREFIX}{task_id}"
        value = await self._client.get(key)
        if value:
            return TaskStatus(value.decode())
        return None

    async def append_output(self, task_id: str, chunk: str) -> None:
        key = f"{self.TASK_OUTPUT_PREFIX}{task_id}"
        await self._client.append(key, chunk)

    async def get_output(self, task_id: str) -> str:
        key = f"{self.TASK_OUTPUT_PREFIX}{task_id}"
        value = await self._client.get(key)
        return value.decode() if value else ""
```

#### Step 3.2: Task Worker

**Test First (test_worker.py)**:
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from agent_engine.core.worker import TaskWorker
from agent_engine.core.queue_manager import TaskStatus

@pytest.fixture
def mock_queue_manager():
    manager = AsyncMock()
    return manager

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session

@pytest.fixture
def mock_cli_executor():
    executor = AsyncMock()
    return executor

@pytest.mark.asyncio
async def test_worker_processes_task(mock_queue_manager, mock_db_session, mock_cli_executor):
    mock_queue_manager.pop_task.side_effect = ["task-123", None]

    worker = TaskWorker(
        queue_manager=mock_queue_manager,
        db_session_factory=lambda: mock_db_session,
        cli_executor=mock_cli_executor,
    )

    # Run worker for one iteration
    await worker._process_single_task()

    mock_cli_executor.execute.assert_called()

@pytest.mark.asyncio
async def test_worker_respects_concurrency_limit():
    worker = TaskWorker(max_concurrent_tasks=2)
    assert worker.semaphore._value == 2

@pytest.mark.asyncio
async def test_worker_updates_task_status(mock_queue_manager, mock_db_session, mock_cli_executor):
    from agent_engine.core.cli.base import CLIResult

    mock_cli_executor.execute.return_value = CLIResult(
        success=True,
        output="result",
        clean_output="result",
        cost_usd=0.01,
        input_tokens=100,
        output_tokens=50,
    )

    worker = TaskWorker(
        queue_manager=mock_queue_manager,
        db_session_factory=lambda: mock_db_session,
        cli_executor=mock_cli_executor,
    )

    await worker._process_task("task-123")

    mock_queue_manager.set_task_status.assert_any_call("task-123", TaskStatus.RUNNING)
    mock_queue_manager.set_task_status.assert_any_call("task-123", TaskStatus.COMPLETED)

@pytest.mark.asyncio
async def test_worker_handles_failure(mock_queue_manager, mock_db_session, mock_cli_executor):
    from agent_engine.core.cli.base import CLIResult

    mock_cli_executor.execute.return_value = CLIResult(
        success=False,
        output="",
        clean_output="",
        cost_usd=0.0,
        input_tokens=0,
        output_tokens=0,
        error="CLI error",
    )

    worker = TaskWorker(
        queue_manager=mock_queue_manager,
        db_session_factory=lambda: mock_db_session,
        cli_executor=mock_cli_executor,
    )

    await worker._process_task("task-123")

    mock_queue_manager.set_task_status.assert_called_with("task-123", TaskStatus.FAILED)

@pytest.mark.asyncio
async def test_worker_graceful_shutdown():
    worker = TaskWorker()
    worker.running = True

    task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.1)

    await worker.stop()
    await asyncio.sleep(0.1)

    assert worker.running is False
```

**Implementation (worker.py)**:
Port from `claude-code-agent/workers/task_worker.py` with modular design.

---

### Phase 4: Database Models (Week 4-5)

**Goal**: Implement PostgreSQL models with SQLAlchemy.

#### Step 4.1: Base Models

**Test First (test_models.py)**:
```python
import pytest
from datetime import datetime, timezone
from agent_engine.models.task import TaskDB, TaskStatus
from agent_engine.models.session import SessionDB
from agent_engine.models.conversation import ConversationDB, ConversationMessageDB

def test_task_model_fields():
    task = TaskDB(
        task_id="task-123",
        session_id="session-456",
        user_id="user-789",
        status=TaskStatus.PENDING,
        input_message="Test message",
        agent_type="brain",
    )
    assert task.task_id == "task-123"
    assert task.status == TaskStatus.PENDING

def test_task_status_enum():
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"

def test_session_model_fields():
    session = SessionDB(
        session_id="session-123",
        user_id="user-456",
        machine_id="machine-001",
    )
    assert session.session_id == "session-123"
    assert session.active is True

def test_conversation_model_fields():
    conv = ConversationDB(
        conversation_id="conv-123",
        user_id="user-456",
        title="Test Conversation",
    )
    assert conv.conversation_id == "conv-123"
    assert conv.total_cost_usd == 0.0
```

**Implementation**: Port models from `claude-code-agent/core/database/models.py`.

---

### Phase 5: Agent Definitions (Week 5-6)

**Goal**: Migrate 13 specialized agents to the new structure.

#### Step 5.1: Agent Registry

**Test First (test_agent_registry.py)**:
```python
import pytest
from pathlib import Path
from agent_engine.agents.registry import AgentRegistry, AgentDefinition

def test_registry_loads_agents():
    registry = AgentRegistry(agents_dir=Path("agent_engine/agents"))
    agents = registry.list_agents()
    assert "brain" in agents
    assert "planning" in agents
    assert "executor" in agents

def test_registry_get_agent():
    registry = AgentRegistry(agents_dir=Path("agent_engine/agents"))
    brain = registry.get_agent("brain")
    assert brain is not None
    assert brain.name == "brain"
    assert brain.model == "opus"

def test_agent_definition_from_markdown():
    content = '''---
name: test-agent
description: Test agent
model: sonnet
tools: Read, Write
---
# Test Agent
Instructions here.
'''
    agent = AgentDefinition.from_markdown(content)
    assert agent.name == "test-agent"
    assert agent.model == "sonnet"
    assert "Read" in agent.tools
```

**Implementation (agents/registry.py)**:
```python
from dataclasses import dataclass
from pathlib import Path
import re
import yaml

@dataclass
class AgentDefinition:
    name: str
    description: str
    model: str
    tools: list[str]
    skills: list[str]
    content: str

    @classmethod
    def from_markdown(cls, content: str) -> "AgentDefinition":
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            raise ValueError("Invalid agent markdown format")

        metadata = yaml.safe_load(frontmatter_match.group(1))
        body = frontmatter_match.group(2)

        tools_str = metadata.get("tools", "")
        tools = [t.strip() for t in tools_str.split(",") if t.strip()]

        skills = metadata.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]

        return cls(
            name=metadata["name"],
            description=metadata.get("description", ""),
            model=metadata.get("model", "sonnet"),
            tools=tools,
            skills=skills,
            content=body,
        )

class AgentRegistry:
    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir
        self._cache: dict[str, AgentDefinition] = {}

    def list_agents(self) -> list[str]:
        agents = []
        for path in self.agents_dir.glob("*.md"):
            agents.append(path.stem)
        return agents

    def get_agent(self, name: str) -> AgentDefinition | None:
        if name in self._cache:
            return self._cache[name]

        path = self.agents_dir / f"{name}.md"
        if not path.exists():
            return None

        content = path.read_text()
        agent = AgentDefinition.from_markdown(content)
        self._cache[name] = agent
        return agent
```

#### Step 5.2: Migrate Agent Definitions

Copy and adapt agent markdown files from `claude-code-agent/.claude/agents/`:

1. `brain.md` - Central orchestrator
2. `planning.md` - Discovery + PLAN.md
3. `executor.md` - TDD implementation
4. `verifier.md` - Quality verification
5. `github-issue-handler.md` - GitHub issues
6. `github-pr-review.md` - PR reviews
7. `jira-code-plan.md` - Jira tickets
8. `slack-inquiry.md` - Slack Q&A
9. `service-integrator.md` - External services
10. `self-improvement.md` - Learning
11. `agent-creator.md` - Dynamic agents
12. `skill-creator.md` - Dynamic skills
13. `webhook-generator.md` - Webhook config

---

### Phase 6: Skills System (Week 6-7)

**Goal**: Migrate skills with modular structure.

#### Step 6.1: Skill Registry

**Test First (test_skill_registry.py)**:
```python
import pytest
from pathlib import Path
from agent_engine.skills.registry import SkillRegistry, SkillDefinition

def test_registry_loads_skills():
    registry = SkillRegistry(skills_dir=Path("agent_engine/skills"))
    skills = registry.list_skills()
    assert "github-operations" in skills
    assert "jira-operations" in skills

def test_skill_has_scripts():
    registry = SkillRegistry(skills_dir=Path("agent_engine/skills"))
    skill = registry.get_skill("github-operations")
    assert skill.scripts is not None
    assert len(skill.scripts) > 0
```

**Implementation (skills/registry.py)**:
```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SkillDefinition:
    name: str
    description: str
    scripts: list[Path]
    readme_content: str

    @classmethod
    def from_directory(cls, skill_dir: Path) -> "SkillDefinition":
        readme = skill_dir / "README.md"
        readme_content = readme.read_text() if readme.exists() else ""

        scripts_dir = skill_dir / "scripts"
        scripts = list(scripts_dir.glob("*")) if scripts_dir.exists() else []

        return cls(
            name=skill_dir.name,
            description=cls._extract_description(readme_content),
            scripts=scripts,
            readme_content=readme_content,
        )

    @staticmethod
    def _extract_description(readme: str) -> str:
        lines = readme.split("\n")
        for line in lines:
            if line.strip() and not line.startswith("#"):
                return line.strip()
        return ""

class SkillRegistry:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self._cache: dict[str, SkillDefinition] = {}

    def list_skills(self) -> list[str]:
        skills = []
        for path in self.skills_dir.iterdir():
            if path.is_dir() and not path.name.startswith("_"):
                skills.append(path.name)
        return skills

    def get_skill(self, name: str) -> SkillDefinition | None:
        if name in self._cache:
            return self._cache[name]

        skill_dir = self.skills_dir / name
        if not skill_dir.exists():
            return None

        skill = SkillDefinition.from_directory(skill_dir)
        self._cache[name] = skill
        return skill
```

#### Step 6.2: Migrate Skills

Copy from `claude-code-agent/.claude/skills/`:

1. `discovery/` - Code discovery
2. `testing/` - TDD phases
3. `code-refactoring/` - Refactoring patterns
4. `github-operations/` - GitHub API
5. `jira-operations/` - Jira API
6. `slack-operations/` - Slack API
7. `human-approval/` - Approval workflow
8. `verification/` - Quality verification
9. `webhook-management/` - Webhook config

---

### Phase 7: Webhook Handlers (Week 7-8)

**Goal**: Implement webhook handlers for API Gateway.

#### Step 7.1: GitHub Webhook Handler

**Test First (test_github_webhook.py)**:
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from api_gateway.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_github_webhook_validates_signature(client):
    response = client.post(
        "/webhooks/github",
        json={"action": "opened"},
        headers={"X-Hub-Signature-256": "invalid"},
    )
    assert response.status_code == 401

def test_github_webhook_accepts_valid_payload(client):
    payload = {
        "action": "created",
        "comment": {"body": "@agent analyze", "id": 123},
        "issue": {"number": 1},
        "repository": {"full_name": "owner/repo"},
    }

    with patch("api_gateway.webhooks.github.handler.create_task") as mock:
        mock.return_value = {"task_id": "task-123"}
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issue_comment"},
        )

    assert response.status_code == 200

def test_github_webhook_ignores_bot_comments(client):
    payload = {
        "action": "created",
        "comment": {"body": "@agent analyze", "user": {"login": "github-actions[bot]"}},
        "issue": {"number": 1},
        "repository": {"full_name": "owner/repo"},
    }

    response = client.post(
        "/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "issue_comment"},
    )

    assert response.status_code == 200
    assert response.json().get("action") == "ignored"
```

**Implementation**: Port from `claude-code-agent/api/webhooks/github/`.

---

### Phase 8: MCP Servers (Week 8-9)

**Goal**: Implement MCP servers for external services.

#### Step 8.1: GitHub MCP (Official)

Use official `github/github-mcp-server`:

**Dockerfile (mcp-servers/github-mcp/Dockerfile)**:
```dockerfile
FROM node:20-alpine

WORKDIR /app

RUN npm install -g @anthropic-ai/github-mcp-server

ENV PORT=9001
ENV GITHUB_API_URL=http://github-api:3001

EXPOSE 9001

CMD ["github-mcp-server", "--port", "9001"]
```

#### Step 8.2: Jira MCP (Custom FastMCP)

**Test First (test_jira_mcp.py)**:
```python
import pytest
from unittest.mock import AsyncMock
from mcp_servers.jira.server import JiraMCPServer

@pytest.fixture
def jira_server():
    return JiraMCPServer(api_url="http://jira-api:3002")

@pytest.mark.asyncio
async def test_get_issue_tool(jira_server):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "key": "PROJ-123",
            "fields": {"summary": "Test issue"},
        }

        result = await jira_server.get_issue("PROJ-123")
        assert result["key"] == "PROJ-123"

@pytest.mark.asyncio
async def test_post_comment_tool(jira_server):
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value.status_code = 201

        result = await jira_server.post_comment("PROJ-123", "Test comment")
        assert result["success"] is True
```

**Implementation (mcp-servers/jira/server.py)**:
```python
from fastmcp import FastMCP
import httpx

mcp = FastMCP("jira-mcp")

class JiraMCPServer:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.client = httpx.AsyncClient(base_url=api_url)

@mcp.tool()
async def get_issue(issue_key: str) -> dict:
    """Get Jira issue details."""
    response = await server.client.get(f"/issues/{issue_key}")
    return response.json()

@mcp.tool()
async def post_comment(issue_key: str, comment: str) -> dict:
    """Post comment to Jira issue."""
    response = await server.client.post(
        f"/issues/{issue_key}/comments",
        json={"body": comment},
    )
    return {"success": response.status_code == 201}

@mcp.tool()
async def search_issues(jql: str, max_results: int = 50) -> list[dict]:
    """Search Jira issues using JQL."""
    response = await server.client.get(
        "/search",
        params={"jql": jql, "maxResults": max_results},
    )
    return response.json().get("issues", [])

server = JiraMCPServer(api_url=os.getenv("JIRA_API_URL", "http://jira-api:3002"))
```

---

### Phase 9: API Services (Week 9-10)

**Goal**: Implement REST API wrappers for external services.

#### Step 9.1: GitHub API Service

**Test First (test_github_api.py)**:
```python
import pytest
from fastapi.testclient import TestClient
from api_services.github.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_issue(client):
    with patch("api_services.github.client.GitHubClient.get_issue") as mock:
        mock.return_value = {"number": 1, "title": "Test"}
        response = client.get("/issues/owner/repo/1")
        assert response.status_code == 200

def test_post_comment(client):
    with patch("api_services.github.client.GitHubClient.post_issue_comment") as mock:
        mock.return_value = {"id": 123}
        response = client.post(
            "/issues/owner/repo/1/comments",
            json={"body": "Test comment"},
        )
        assert response.status_code == 201
```

**Implementation (api-services/github/main.py)**:
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os

app = FastAPI(title="GitHub API Service")

class GitHubClient:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def post_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers=self.headers,
                json={"body": body},
            )
            response.raise_for_status()
            return response.json()

github_client = GitHubClient()

class CommentRequest(BaseModel):
    body: str

@app.get("/issues/{owner}/{repo}/{issue_number}")
async def get_issue(owner: str, repo: str, issue_number: int):
    return await github_client.get_issue(owner, repo, issue_number)

@app.post("/issues/{owner}/{repo}/{issue_number}/comments", status_code=201)
async def post_comment(owner: str, repo: str, issue_number: int, request: CommentRequest):
    return await github_client.post_issue_comment(owner, repo, issue_number, request.body)
```

---

### Phase 10: Dashboard (Week 10-11)

**Goal**: Implement internal dashboard API and external React dashboard.

#### Step 10.1: Internal Dashboard API

**Test First (test_dashboard_api.py)**:
```python
import pytest
from fastapi.testclient import TestClient
from dashboard_api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_tasks(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_task_logs(client):
    with patch("dashboard_api.services.task_manager.get_task_logs") as mock:
        mock.return_value = ["log line 1", "log line 2"]
        response = client.get("/api/tasks/task-123/logs")
        assert response.status_code == 200

def test_get_metrics(client):
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert "total_tasks" in response.json()

def test_websocket_connection(client):
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert "type" in data
```

---

### Phase 11: Integration & E2E Testing (Week 11-12)

**Goal**: Full system integration testing.

#### Step 11.1: Integration Tests

**Test Full Webhook Flow**:
```python
import pytest
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="module")
def compose():
    with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
        compose.wait_for("api-gateway")
        compose.wait_for("agent-engine")
        yield compose

def test_webhook_to_task_flow(compose):
    gateway_url = compose.get_service_url("api-gateway", 8000)

    payload = {
        "action": "created",
        "comment": {"body": "@agent analyze", "id": 123},
        "issue": {"number": 1},
        "repository": {"full_name": "owner/repo"},
    }

    response = httpx.post(f"{gateway_url}/webhooks/github", json=payload)
    assert response.status_code == 200

    task_id = response.json()["task_id"]

    # Wait for task to complete
    for _ in range(30):
        status = httpx.get(f"{gateway_url}/api/tasks/{task_id}/status")
        if status.json()["status"] in ["completed", "failed"]:
            break
        time.sleep(1)

    assert status.json()["status"] == "completed"
```

---

## Directory Structure Summary

```
agent-bot/
├── CLAUDE.md                           # Root documentation
├── docker-compose.yml                  # Main orchestration
├── Makefile                            # Dev commands
├── .env.example
│
├── agent-engine-package/               # Core agent engine (installable package)
│   ├── pyproject.toml
│   ├── agent_engine/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── cli/
│   │   │   │   ├── base.py
│   │   │   │   ├── executor.py
│   │   │   │   ├── sanitization.py
│   │   │   │   └── providers/
│   │   │   │       ├── claude/
│   │   │   │       └── cursor/
│   │   │   ├── worker.py
│   │   │   ├── queue_manager.py
│   │   │   └── config.py
│   │   ├── models/
│   │   │   ├── task.py
│   │   │   ├── session.py
│   │   │   └── conversation.py
│   │   ├── agents/
│   │   │   ├── registry.py
│   │   │   ├── brain.md
│   │   │   ├── planning.md
│   │   │   ├── executor.md
│   │   │   ├── verifier.md
│   │   │   └── ... (13 agents)
│   │   ├── skills/
│   │   │   ├── registry.py
│   │   │   ├── github-operations/
│   │   │   ├── jira-operations/
│   │   │   └── ... (9 skills)
│   │   └── memory/
│   │       ├── code/
│   │       ├── agents/
│   │       └── process/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── conftest.py
│
├── agent-engine/                       # Agent engine container
│   ├── Dockerfile
│   ├── CLAUDE.md
│   ├── mcp.json
│   └── .claude/
│       └── settings.json
│
├── api-gateway/                        # API Gateway container
│   ├── Dockerfile
│   ├── CLAUDE.md
│   ├── main.py
│   └── webhooks/
│       ├── github/
│       ├── jira/
│       ├── slack/
│       └── sentry/
│
├── mcp-servers/                        # MCP servers
│   ├── docker-compose.mcp.yml
│   ├── github-mcp/
│   ├── jira-mcp/
│   ├── slack-mcp/
│   └── sentry-mcp/
│
├── api-services/                       # API service wrappers
│   ├── docker-compose.services.yml
│   ├── github-api/
│   ├── jira-api/
│   ├── slack-api/
│   └── sentry-api/
│
├── internal-dashboard-api/             # Dashboard API
│   ├── Dockerfile
│   ├── CLAUDE.md
│   └── main.py
│
├── external-dashboard/                 # React dashboard
│   ├── Dockerfile
│   └── src/
│
├── knowledge-graph/                    # Knowledge graph
│   └── Dockerfile
│
└── docs/
    └── architecture/
```

---

## TDD Checklist Per Phase

### Phase 1: Foundation
- [ ] test_project_structure.py
- [ ] test_cli_base.py
- [ ] test_config.py
- [ ] test_docker_infrastructure.py

### Phase 2: CLI Providers
- [ ] test_sanitization.py
- [ ] test_claude_provider.py
- [ ] test_cursor_provider.py
- [ ] test_executor.py

### Phase 3: Queue & Worker
- [ ] test_queue_manager.py
- [ ] test_worker.py
- [ ] test_task_lifecycle.py

### Phase 4: Database Models
- [ ] test_task_model.py
- [ ] test_session_model.py
- [ ] test_conversation_model.py
- [ ] test_migrations.py

### Phase 5: Agents
- [ ] test_agent_registry.py
- [ ] test_brain_agent.py
- [ ] test_agent_definitions.py

### Phase 6: Skills
- [ ] test_skill_registry.py
- [ ] test_github_operations.py
- [ ] test_jira_operations.py

### Phase 7: Webhooks
- [ ] test_github_webhook.py
- [ ] test_jira_webhook.py
- [ ] test_slack_webhook.py

### Phase 8: MCP Servers
- [ ] test_jira_mcp.py
- [ ] test_slack_mcp.py
- [ ] test_sentry_mcp.py

### Phase 9: API Services
- [ ] test_github_api.py
- [ ] test_jira_api.py
- [ ] test_slack_api.py

### Phase 10: Dashboard
- [ ] test_dashboard_api.py
- [ ] test_websocket_hub.py

### Phase 11: Integration
- [ ] test_webhook_to_task_flow.py
- [ ] test_mcp_integration.py
- [ ] test_e2e_scenarios.py

---

## Success Criteria

1. **All tests pass** (unit, integration, E2E)
2. **Type coverage**: 100% strict typing, no `any`
3. **Code quality**: No comments, self-explanatory naming
4. **File size**: Max 300 lines per file
5. **Modularity**: Each component independently testable
6. **CLI providers**: Claude and Cursor both working
7. **Webhook flow**: GitHub → Task → Response working
8. **Dashboard**: Real-time task monitoring
9. **Docker**: All 14 containers running
10. **Documentation**: CLAUDE.md files complete

---

## Migration from claude-code-agent

### Files to Port

| Source | Destination | Changes |
|--------|-------------|---------|
| `core/cli/claude.py` | `agent_engine/core/cli/providers/claude/runner.py` | Type hints, no comments |
| `core/cli/base.py` | `agent_engine/core/cli/base.py` | Keep as-is |
| `core/config.py` | `agent_engine/core/config.py` | Add CLI provider enum |
| `workers/task_worker.py` | `agent_engine/core/worker.py` | Modular functions |
| `core/database/models.py` | `agent_engine/models/*.py` | Split into modules |
| `.claude/agents/*.md` | `agent_engine/agents/*.md` | Keep as-is |
| `.claude/skills/*` | `agent_engine/skills/*` | Keep structure |
| `api/webhooks/*` | `api-gateway/webhooks/*` | Extract handlers |

### Business Logic to Preserve

1. **Brain orchestration**: Task classification, agent delegation
2. **Approval workflow**: Human-in-the-loop for code changes
3. **Verification loop**: Max 3 iterations, 90% threshold
4. **Response posting**: Automatic posting to GitHub/Jira/Slack
5. **Loop prevention**: Redis tracking of posted comments
6. **Cost tracking**: Token/cost aggregation per task/conversation
7. **Memory system**: Self-improvement learning

---

## Next Steps

1. **Start Phase 1**: Create project structure and base classes
2. **Write tests first**: Follow TDD strictly
3. **Implement incrementally**: One test file at a time
4. **Review after each phase**: Ensure all tests pass before moving on
5. **Document as you go**: Update CLAUDE.md files

---

**Total Estimated Duration**: 12 weeks (3 months)

**Key Milestones**:
- Week 4: CLI providers working
- Week 6: Full agent system working
- Week 9: MCP servers integrated
- Week 12: Production-ready system
