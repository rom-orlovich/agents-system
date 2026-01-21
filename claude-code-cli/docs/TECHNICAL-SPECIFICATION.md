# Technical Specification - Claude Machine Management System

> **Version**: 1.0.0  
> **Last Updated**: 2026-01-21  
> **Status**: DRAFT - Pending Approval  
> **Project Directory**: `claude-code-agent/`

---

> [!CAUTION]
> **WORKFLOW**: Tests pass → `git commit && push` → Update `PROGRESS.md`

---

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Pydantic Models (All Logic Enforcement)](#pydantic-models)
4. [Architecture Patterns](#architecture-patterns)
5. [Implementation Details](#implementation-details)
6. [API Specifications](#api-specifications)
7. [WebSocket Protocol](#websocket-protocol)
8. [Persistence Layer](#persistence-layer)
9. [Authentication System](#authentication-system)
10. [Development Guidelines](#development-guidelines)

---

## Overview

### Vision

A **self-managing machine** where:
- **FastAPI** runs as a daemon (always on) - handles webhooks and dashboard
- **Claude Code CLI** is spawned on-demand per request - does the actual work
- **Sub-agents** = Claude CLI instances running from specific directories

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              CONTAINER (Pod)                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                    FastAPI Server (DAEMON - always running)          │    │
│   │                                                                       │    │
│   │   Webhooks:           Dashboard API:          WebSocket:             │    │
│   │   /webhooks/github    /api/chat               /ws/{session_id}       │    │
│   │   /webhooks/jira      /api/tasks                                     │    │
│   │   /webhooks/sentry    /api/agents                                    │    │
│   │   /webhooks/{custom}  /api/upload                                    │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                         │
│                                     ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                         Task Queue (Redis)                           │    │
│   │                 task_id → {prompt, agent, status, pid}               │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                         │
│                                     ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                         Worker (Python async)                        │    │
│   │                                                                       │    │
│   │   for task in queue:                                                  │    │
│   │       agent_dir = get_agent_directory(task.agent)                    │    │
│   │       process = spawn("claude", "-p", task.prompt, cwd=agent_dir)    │    │
│   │       stream output to WebSocket                                      │    │
│   │       save result to SQLite                                           │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                         │
│                                     ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │              Claude Code CLI (ON-DEMAND - spawn per request)         │    │
│   │                                                                       │    │
│   │   Brain:      cwd=/app/             → reads /app/.claude/CLAUDE.md   │    │
│   │   Planning:   cwd=/app/agents/planning/  → reads its CLAUDE.md       │    │
│   │   Executor:   cwd=/app/agents/executor/  → reads its CLAUDE.md       │    │
│   │   Custom:     cwd=/app/agents/{name}/    → reads its CLAUDE.md       │    │
│   │                                                                       │    │
│   │   ⚡ Starts → Works → Returns Result → Exits                          │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│   /data/ (Persistent Volume)                                                  │
│   ├── db/machine.db (SQLite)                                                 │
│   ├── config/ (webhooks, agents, skills)                                     │
│   └── credentials/ (Claude auth)                                             │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘

KEY:
  DAEMON  = runs forever, waits for requests
  ON-DEMAND = spawns, does work, exits
```

### Core Principles

| Principle | Implementation |
|-----------|----------------|
| **Pydantic Everywhere** | ALL domain logic enforced via Pydantic models with validators |
| **uv Only** | Use `uv` exclusively for package management (no pip) |
| **Type Safety** | Full typing with mypy strict mode |
| **Asyncio Native** | All I/O operations are async |
| **TDD** | Tests for business logic first, implementation second |
| **On-Demand CLI** | Claude CLI spawned per request, not always running |

---

## Technology Stack

### Package Manager

> [!IMPORTANT]
> **MUST USE `uv`** - Do NOT use pip, pipenv, or poetry.

```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package>

# Add dev dependency
uv add --dev <package>

# Run Python
uv run python script.py

# Run tests
uv run pytest tests/

# Run with specific Python version
uv run --python 3.12 python script.py
```

### Core Dependencies

```toml
# pyproject.toml
[project]
name = "claude-machine"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "pydantic>=2.5.0",          # ALL validation
    "pydantic-settings>=2.1.0", # Environment config
    "fastapi>=0.109.0",         # API + WebSocket
    "uvicorn[standard]>=0.27.0", # ASGI server
    "redis>=5.0.0",             # Queue + Cache
    "sqlalchemy>=2.0.0",        # Database ORM
    "aiosqlite>=0.19.0",        # Async SQLite
    "httpx>=0.26.0",            # Async HTTP client
    "websockets>=12.0",         # WebSocket client
    "structlog>=24.1.0",        # Structured logging
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.8.0",
    "ruff>=0.2.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

---

## Pydantic Models

> [!IMPORTANT]
> **ALL business logic MUST be enforced via Pydantic models.**  
> No raw dictionaries. No untyped data. Validators for all rules.

### Core Models

```python
# shared/machine_models.py
"""
ALL domain models with Pydantic validation.
Business rules are ENFORCED here, not in service layer.
"""

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# =============================================================================
# ENUMS (String-based for JSON serialization)
# =============================================================================

class TaskStatus(StrEnum):
    """Task lifecycle states."""
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(StrEnum):
    """Built-in agent types."""
    PLANNING = "planning"
    EXECUTOR = "executor"
    CODE_IMPLEMENTATION = "code_implementation"
    QUESTION_ASKING = "question_asking"
    CONSULTATION = "consultation"
    CUSTOM = "custom"


class EntityType(StrEnum):
    """Dynamic entity types."""
    WEBHOOK = "webhook"
    AGENT = "agent"
    SKILL = "skill"


class AuthStatus(StrEnum):
    """Authentication states."""
    VALID = "valid"
    EXPIRED = "expired"
    REFRESH_NEEDED = "refresh_needed"
    MISSING = "missing"
    RATE_LIMITED = "rate_limited"


# =============================================================================
# BASE CONFIGURATION
# =============================================================================

class MachineConfig(BaseModel):
    """Machine configuration with Pydantic Settings."""
    model_config = ConfigDict(frozen=True)
    
    machine_id: str = Field(..., min_length=1, max_length=64)
    max_concurrent_tasks: int = Field(default=5, ge=1, le=20)
    task_timeout_seconds: int = Field(default=3600, ge=60, le=86400)
    data_dir: Path = Field(default=Path("/data"))
    
    @field_validator("machine_id")
    @classmethod
    def validate_machine_id(cls, v: str) -> str:
        """Machine ID must be alphanumeric with hyphens."""
        import re
        if not re.match(r"^[a-zA-Z0-9-]+$", v):
            raise ValueError("machine_id must be alphanumeric with hyphens only")
        return v


# =============================================================================
# SESSION MODEL (Per-User Tracking)
# =============================================================================

class Session(BaseModel):
    """Dashboard session with per-user tracking."""
    model_config = ConfigDict(validate_assignment=True)
    
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User account ID from Claude auth")
    machine_id: str = Field(..., description="Machine this session connects to")
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    disconnected_at: Optional[datetime] = None
    
    # Metrics (auto-updated)
    total_cost_usd: float = Field(default=0.0, ge=0.0)
    total_tasks: int = Field(default=0, ge=0)
    active_task_ids: List[str] = Field(default_factory=list)
    
    @field_validator("session_id", "user_id", "machine_id")
    @classmethod
    def validate_required_id(cls, v: str) -> str:
        """IDs cannot be empty."""
        if not v or not v.strip():
            raise ValueError("ID cannot be empty")
        return v.strip()
    
    def add_task(self, task_id: str) -> None:
        """Add task to this session."""
        if task_id not in self.active_task_ids:
            self.active_task_ids.append(task_id)
            self.total_tasks += 1
    
    def add_cost(self, cost: float) -> None:
        """Add cost to session total."""
        if cost < 0:
            raise ValueError("Cost cannot be negative")
        self.total_cost_usd += cost


# =============================================================================
# TASK MODEL (With Streaming Support)
# =============================================================================

class Task(BaseModel):
    """Task with full lifecycle and streaming support."""
    model_config = ConfigDict(validate_assignment=True)
    
    task_id: str = Field(..., description="Unique task identifier")
    session_id: str = Field(..., description="Session that created this task")
    user_id: str = Field(..., description="User who owns this task")
    
    # Assignment
    assigned_agent: Optional[str] = Field(None, description="Sub-agent handling this")
    agent_type: AgentType = Field(default=AgentType.PLANNING)
    
    # Status
    status: TaskStatus = Field(default=TaskStatus.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Input/Output
    input_message: str = Field(..., min_length=1)
    output_stream: str = Field(default="", description="Accumulated output")
    result: Optional[str] = None
    error: Optional[str] = None
    
    # Metrics
    cost_usd: float = Field(default=0.0, ge=0.0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    
    # Relationships
    parent_task_id: Optional[str] = None
    source: Literal["dashboard", "webhook", "api"] = "dashboard"
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode="after")
    def validate_status_transitions(self) -> "Task":
        """Ensure valid status transitions."""
        if self.status == TaskStatus.RUNNING and self.started_at is None:
            self.started_at = datetime.utcnow()
        if self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            if self.completed_at is None:
                self.completed_at = datetime.utcnow()
            if self.started_at and self.completed_at:
                self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        return self
    
    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """Check if status transition is valid."""
        valid_transitions = {
            TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.RUNNING: {TaskStatus.WAITING_INPUT, TaskStatus.COMPLETED, 
                                 TaskStatus.FAILED, TaskStatus.CANCELLED},
            TaskStatus.WAITING_INPUT: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.COMPLETED: set(),  # Terminal
            TaskStatus.FAILED: set(),     # Terminal
            TaskStatus.CANCELLED: set(),  # Terminal
        }
        return new_status in valid_transitions.get(self.status, set())
    
    def transition_to(self, new_status: TaskStatus) -> None:
        """Transition to new status with validation."""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")
        self.status = new_status


# =============================================================================
# SUB-AGENT MODEL
# =============================================================================

class SubAgentConfig(BaseModel):
    """Sub-agent configuration."""
    model_config = ConfigDict(frozen=True)
    
    name: str = Field(..., min_length=1, max_length=64)
    agent_type: AgentType = Field(default=AgentType.CUSTOM)
    description: str = Field(default="")
    skill_path: Path = Field(...)
    
    # Execution config
    max_concurrent: int = Field(default=1, ge=1, le=10)
    timeout_seconds: int = Field(default=3600, ge=60)
    priority: int = Field(default=0, ge=0, le=100)
    
    # Built-in vs dynamic
    is_builtin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Name must be lowercase alphanumeric with hyphens/underscores."""
        import re
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError("name must be lowercase alphanumeric with hyphens/underscores")
        return v
    
    @field_validator("skill_path")
    @classmethod
    def validate_skill_path(cls, v: Path) -> Path:
        """Skill path must contain SKILL.md."""
        skill_file = v / "SKILL.md"
        # Note: We validate existence at runtime, not during model creation
        return v


# =============================================================================
# WEBHOOK MODEL
# =============================================================================

class WebhookConfig(BaseModel):
    """Webhook configuration."""
    model_config = ConfigDict(frozen=True)
    
    name: str = Field(..., min_length=1, max_length=64)
    endpoint: str = Field(..., pattern=r"^/webhooks/[a-z0-9-]+$")
    description: str = Field(default="")
    
    # Handler
    handler_path: Path = Field(...)
    target_agent: str = Field(..., description="Agent to route tasks to")
    
    # Security
    requires_signature: bool = Field(default=True)
    signature_header: Optional[str] = Field(default=None)
    secret_env_var: Optional[str] = Field(default=None)
    
    # Metadata
    is_builtin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Name must be lowercase alphanumeric with hyphens."""
        import re
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("name must be lowercase alphanumeric with hyphens")
        return v


# =============================================================================
# SKILL MODEL
# =============================================================================

class SkillConfig(BaseModel):
    """Skill configuration."""
    model_config = ConfigDict(frozen=True)
    
    name: str = Field(..., min_length=1, max_length=64)
    target: str = Field(..., description="'brain' or agent name")
    description: str = Field(default="")
    skill_path: Path = Field(...)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        """Target must be 'brain' or valid agent name."""
        if v != "brain" and not v.strip():
            raise ValueError("target must be 'brain' or a valid agent name")
        return v


# =============================================================================
# CREDENTIAL MODEL
# =============================================================================

class ClaudeCredentials(BaseModel):
    """Claude authentication credentials."""
    model_config = ConfigDict(validate_assignment=True)
    
    access_token: str = Field(..., min_length=10)
    refresh_token: str = Field(..., min_length=10)
    expires_at: int = Field(..., description="Expiry timestamp in milliseconds")
    token_type: str = Field(default="Bearer")
    account_id: Optional[str] = None
    
    @property
    def expires_at_datetime(self) -> datetime:
        """Convert to datetime."""
        return datetime.fromtimestamp(self.expires_at / 1000)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() >= self.expires_at_datetime
    
    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (< 30 min left)."""
        remaining = (self.expires_at_datetime - datetime.utcnow()).total_seconds()
        return remaining < 1800  # 30 minutes
    
    def get_status(self) -> AuthStatus:
        """Get current auth status."""
        if self.is_expired:
            return AuthStatus.EXPIRED
        if self.needs_refresh:
            return AuthStatus.REFRESH_NEEDED
        return AuthStatus.VALID


# =============================================================================
# WEBSOCKET MESSAGE MODELS
# =============================================================================

class WebSocketMessage(BaseModel):
    """Base WebSocket message."""
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskCreatedMessage(WebSocketMessage):
    """Task created event."""
    type: Literal["task.created"] = "task.created"
    task_id: str
    agent: str
    status: TaskStatus


class TaskOutputMessage(WebSocketMessage):
    """Task output chunk event."""
    type: Literal["task.output"] = "task.output"
    task_id: str
    chunk: str


class TaskMetricsMessage(WebSocketMessage):
    """Task metrics update event."""
    type: Literal["task.metrics"] = "task.metrics"
    task_id: str
    cost_usd: float
    tokens: int
    duration_seconds: float


class TaskCompletedMessage(WebSocketMessage):
    """Task completed event."""
    type: Literal["task.completed"] = "task.completed"
    task_id: str
    result: str
    cost_usd: float


class TaskFailedMessage(WebSocketMessage):
    """Task failed event."""
    type: Literal["task.failed"] = "task.failed"
    task_id: str
    error: str


class UserInputMessage(WebSocketMessage):
    """User input to task."""
    type: Literal["task.input"] = "task.input"
    task_id: str
    message: str


class TaskStopMessage(WebSocketMessage):
    """Stop task command."""
    type: Literal["task.stop"] = "task.stop"
    task_id: str


class ChatMessage(WebSocketMessage):
    """Chat with Brain."""
    type: Literal["chat.message"] = "chat.message"
    message: str
    

# Union type for all WebSocket messages
WSMessage = (TaskCreatedMessage | TaskOutputMessage | TaskMetricsMessage | 
             TaskCompletedMessage | TaskFailedMessage | UserInputMessage | 
             TaskStopMessage | ChatMessage)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateWebhookRequest(BaseModel):
    """Request to create a webhook."""
    method: Literal["describe", "upload", "form"]
    description: Optional[str] = None  # For method="describe"
    file_content: Optional[str] = None  # For method="upload"
    form_data: Optional[Dict[str, Any]] = None  # For method="form"
    
    @model_validator(mode="after")
    def validate_method_data(self) -> "CreateWebhookRequest":
        """Ensure correct data for method."""
        if self.method == "describe" and not self.description:
            raise ValueError("description required for method='describe'")
        if self.method == "upload" and not self.file_content:
            raise ValueError("file_content required for method='upload'")
        if self.method == "form" and not self.form_data:
            raise ValueError("form_data required for method='form'")
        return self


class CreateAgentRequest(BaseModel):
    """Request to create a sub-agent."""
    method: Literal["describe", "upload", "form"]
    description: Optional[str] = None
    folder_content: Optional[Dict[str, str]] = None  # filename -> content
    form_data: Optional[Dict[str, Any]] = None
    
    @model_validator(mode="after")
    def validate_method_data(self) -> "CreateAgentRequest":
        """Ensure correct data for method."""
        if self.method == "describe" and not self.description:
            raise ValueError("description required for method='describe'")
        if self.method == "upload" and not self.folder_content:
            raise ValueError("folder_content required for method='upload'")
        if self.method == "form" and not self.form_data:
            raise ValueError("form_data required for method='form'")
        return self


class UploadCredentialsRequest(BaseModel):
    """Request to upload credentials."""
    credentials: ClaudeCredentials
    

class APIResponse(BaseModel):
    """Standard API response."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

---

## Architecture Patterns

### Pattern 1: Registry Pattern (Extensibility)

```python
# agents/unified/registry.py
"""Generic registry pattern for extensible entities."""

from typing import TypeVar, Generic, Dict, Optional, Type
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Registry(Generic[T]):
    """Type-safe registry for Pydantic models."""
    
    def __init__(self):
        self._items: Dict[str, T] = {}
    
    def register(self, name: str, item: T) -> None:
        """Register an item."""
        if name in self._items:
            raise ValueError(f"Item '{name}' already registered")
        self._items[name] = item
    
    def get(self, name: str) -> Optional[T]:
        """Get item by name."""
        return self._items.get(name)
    
    def list_all(self) -> list[T]:
        """List all registered items."""
        return list(self._items.values())
    
    def unregister(self, name: str) -> bool:
        """Unregister an item."""
        if name in self._items:
            del self._items[name]
            return True
        return False


# Usage
agent_registry = Registry[SubAgentConfig]()
webhook_registry = Registry[WebhookConfig]()
```

### Pattern 2: Background Task Manager (Asyncio)

```python
# agents/unified/background_manager.py
"""Asyncio-based background task manager."""

import asyncio
from typing import Dict, AsyncIterator
from contextlib import asynccontextmanager

from shared.machine_models import Task, TaskStatus


class BackgroundTaskManager:
    """Manages sub-agents as asyncio background tasks."""
    
    def __init__(self, max_workers: int = 5):
        self._semaphore = asyncio.Semaphore(max_workers)
        self._tasks: Dict[str, asyncio.Task] = {}
        self._output_queues: Dict[str, asyncio.Queue] = {}
        self._input_queues: Dict[str, asyncio.Queue] = {}
    
    async def submit(self, task: Task, runner_coro) -> str:
        """Submit task to run in background."""
        async def wrapped():
            async with self._semaphore:
                return await runner_coro
        
        self._output_queues[task.task_id] = asyncio.Queue()
        self._input_queues[task.task_id] = asyncio.Queue()
        
        asyncio_task = asyncio.create_task(wrapped())
        self._tasks[task.task_id] = asyncio_task
        
        return task.task_id
    
    async def stream_output(self, task_id: str) -> AsyncIterator[str]:
        """Yield output chunks as they're produced."""
        queue = self._output_queues.get(task_id)
        if not queue:
            return
        
        while True:
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=30.0)
                if chunk is None:  # End of stream
                    break
                yield chunk
            except asyncio.TimeoutError:
                continue
    
    async def send_input(self, task_id: str, message: str) -> bool:
        """Send user input to running task."""
        queue = self._input_queues.get(task_id)
        if queue:
            await queue.put(message)
            return True
        return False
    
    async def stop(self, task_id: str) -> bool:
        """Stop a running task."""
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            return True
        return False
```

### Pattern 4: Claude CLI Runner (Headless Execution)

> [!IMPORTANT]
> **This is how Claude Code CLI is actually executed** - using subprocess with `--print` flag for headless mode.

```python
# core/cli_runner.py
"""Execute Claude Code CLI in headless mode (like today's implementation)."""

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator, Optional
from dataclasses import dataclass


@dataclass
class CLIResult:
    """Result from Claude CLI execution."""
    success: bool
    output: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    error: Optional[str] = None


async def run_claude_cli(
    prompt: str,
    working_dir: Path,
    output_queue: asyncio.Queue,
    timeout_seconds: int = 3600,
) -> CLIResult:
    """
    Execute Claude Code CLI in headless mode.
    
    This is the actual subprocess execution - same as today's implementation.
    
    Args:
        prompt: The task prompt to send to Claude
        working_dir: Directory to run from (determines which CLAUDE.md is read)
        output_queue: Queue to stream output chunks to
        timeout_seconds: Maximum execution time
        
    Returns:
        CLIResult with output, cost, and token counts
    """
    
    # Build the command - SAME AS TODAY
    cmd = [
        "claude",
        "--print",                    # Headless mode - no interactive UI
        "--output-format", "json",    # JSON output for parsing
        "--dangerously-skip-permissions",  # Skip permission prompts
        "-p", prompt,                 # The prompt/task
    ]
    
    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(working_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            **os.environ,
            "CLAUDE_TASK_ID": task_id,  # For status monitoring
        }
    )
    
    accumulated_output = []
    cost_usd = 0.0
    input_tokens = 0
    output_tokens = 0
    
    try:
        # Stream stdout in real-time
        async def read_stream():
            nonlocal cost_usd, input_tokens, output_tokens
            
            async for line in process.stdout:
                line_str = line.decode().strip()
                if not line_str:
                    continue
                    
                try:
                    # Parse JSON output from Claude CLI
                    data = json.loads(line_str)
                    
                    if data.get("type") == "content":
                        # Text output - stream to queue
                        chunk = data.get("content", "")
                        accumulated_output.append(chunk)
                        await output_queue.put(chunk)
                        
                    elif data.get("type") == "result":
                        # Final result with metrics
                        cost_usd = data.get("cost_usd", 0.0)
                        input_tokens = data.get("input_tokens", 0)
                        output_tokens = data.get("output_tokens", 0)
                        
                except json.JSONDecodeError:
                    # Plain text output
                    accumulated_output.append(line_str)
                    await output_queue.put(line_str)
        
        # Run with timeout
        await asyncio.wait_for(read_stream(), timeout=timeout_seconds)
        await process.wait()
        
        # Signal end of stream
        await output_queue.put(None)
        
        return CLIResult(
            success=process.returncode == 0,
            output="".join(accumulated_output),
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=None if process.returncode == 0 else f"Exit code: {process.returncode}"
        )
        
    except asyncio.TimeoutError:
        process.kill()
        await output_queue.put(None)
        return CLIResult(
            success=False,
            output="".join(accumulated_output),
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error="Timeout exceeded"
        )


# Usage example
async def execute_task(task: Task, agent_dir: Path) -> CLIResult:
    """Execute a task using Claude CLI."""
    output_queue = asyncio.Queue()
    
    # Start CLI execution
    result = await run_claude_cli(
        prompt=task.input_message,
        working_dir=agent_dir,
        output_queue=output_queue,
    )
    
    return result
```

### Pattern 5: Webhook with Commands System

> [!IMPORTANT]
> **Each webhook can have multiple commands** that users can trigger via comments/messages.

```python
# webhooks/models.py
"""Webhook configuration with command system."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from enum import StrEnum


class WebhookCommand(BaseModel):
    """A command that can be triggered via webhook."""
    
    name: str = Field(..., description="Command name, e.g. 'approve', 'improve'")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    description: str = Field(default="")
    target_agent: str = Field(..., description="Which agent handles this command")
    prompt_template: str = Field(..., description="Prompt template with {placeholders}")
    requires_approval: bool = Field(default=False)
    
    # Example:
    # name: "improve"
    # aliases: ["enhance", "fix"]
    # target_agent: "executor"
    # prompt_template: "Improve the code based on this feedback: {comment}"


class WebhookConfig(BaseModel):
    """Complete webhook configuration with commands."""
    
    name: str = Field(..., min_length=1)
    endpoint: str = Field(..., pattern=r"^/webhooks/[a-z0-9-]+$")
    source: Literal["github", "jira", "sentry", "slack", "gitlab", "custom"]
    
    # Commands this webhook supports
    commands: List[WebhookCommand] = Field(default_factory=list)
    
    # Default command when no specific command is detected
    default_command: Optional[str] = None
    
    # Command prefix for detection (e.g., "@agent" or "/claude")
    command_prefix: str = Field(default="@agent")
    
    # Signature verification
    secret_env_var: Optional[str] = None
    signature_header: Optional[str] = None


# Example webhook configuration
GITHUB_WEBHOOK_CONFIG = WebhookConfig(
    name="github",
    endpoint="/webhooks/github",
    source="github",
    command_prefix="@agent",
    secret_env_var="GITHUB_WEBHOOK_SECRET",
    signature_header="X-Hub-Signature-256",
    commands=[
        WebhookCommand(
            name="approve",
            aliases=["lgtm", "ship"],
            description="Approve the plan and start execution",
            target_agent="executor",
            prompt_template="Execute the approved plan for PR #{pr_number}",
        ),
        WebhookCommand(
            name="improve",
            aliases=["enhance", "fix", "update"],
            description="Improve the code based on feedback",
            target_agent="executor",
            prompt_template="Improve the code: {comment}",
        ),
        WebhookCommand(
            name="plan",
            aliases=["analyze", "review"],
            description="Create a plan for the issue",
            target_agent="planning",
            prompt_template="Analyze and create a plan: {issue_description}",
        ),
        WebhookCommand(
            name="question",
            aliases=["ask", "help"],
            description="Ask a question about the code",
            target_agent="planning",
            prompt_template="Answer this question: {comment}",
        ),
    ],
    default_command="plan",
)
```

```python
# webhooks/command_parser.py
"""Parse commands from webhook payloads."""

import re
from typing import Optional, Tuple


class CommandParser:
    """Parse commands from webhook comments/messages."""
    
    def __init__(self, config: WebhookConfig):
        self.config = config
        self.prefix = config.command_prefix
        
    def parse(self, text: str) -> Tuple[Optional[WebhookCommand], dict]:
        """
        Parse command from text.
        
        Returns:
            Tuple of (command, extracted_variables) or (None, {}) if no command found
        """
        # Pattern: @agent <command> [args]
        pattern = rf"{re.escape(self.prefix)}\s+(\w+)(?:\s+(.+))?"
        match = re.search(pattern, text, re.IGNORECASE)
        
        if not match:
            # No command found, use default
            if self.config.default_command:
                cmd = self._find_command(self.config.default_command)
                return cmd, {"comment": text}
            return None, {}
        
        command_name = match.group(1).lower()
        args = match.group(2) or ""
        
        # Find matching command
        cmd = self._find_command(command_name)
        if cmd:
            return cmd, {"comment": args, "full_text": text}
        
        return None, {}
    
    def _find_command(self, name: str) -> Optional[WebhookCommand]:
        """Find command by name or alias."""
        for cmd in self.config.commands:
            if cmd.name == name or name in cmd.aliases:
                return cmd
        return None


# Usage
parser = CommandParser(GITHUB_WEBHOOK_CONFIG)
command, vars = parser.parse("@agent improve add error handling")
# command.name = "improve"
# vars = {"comment": "add error handling", "full_text": "..."}
```

### Pattern 3: WebSocket Hub (Real-Time)

```python
# services/dashboard/api/websocket_hub.py
"""WebSocket connection hub for real-time updates."""

import asyncio
from typing import Dict, Set
from fastapi import WebSocket

from shared.machine_models import WSMessage


class WebSocketHub:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}  # session_id -> connections
    
    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Register a WebSocket connection."""
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """Remove a WebSocket connection."""
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
    
    async def send_to_session(self, session_id: str, message: WSMessage) -> None:
        """Send message to all connections in a session."""
        connections = self._connections.get(session_id, set())
        for ws in connections:
            try:
                await ws.send_json(message.model_dump())
            except Exception:
                pass  # Connection might be closed
    
    async def broadcast(self, message: WSMessage) -> None:
        """Broadcast message to all connections."""
        for session_id in self._connections:
            await self.send_to_session(session_id, message)
```

---

## API Specifications

### REST Endpoints

| Method | Endpoint | Description | Request Model | Response Model |
|--------|----------|-------------|---------------|----------------|
| GET | `/api/status` | Machine status | - | `MachineStatus` |
| GET | `/api/sessions/{id}` | Get session | - | `Session` |
| GET | `/api/tasks` | List tasks | Query params | `List[Task]` |
| GET | `/api/tasks/{id}` | Get task | - | `Task` |
| POST | `/api/tasks/{id}/stop` | Stop task | - | `APIResponse` |
| POST | `/api/chat` | Chat with Brain | `ChatMessage` | `APIResponse` |
| GET | `/api/agents` | List sub-agents | - | `List[SubAgentConfig]` |
| POST | `/api/agents` | Create sub-agent | `CreateAgentRequest` | `SubAgentConfig` |
| GET | `/api/webhooks` | List webhooks | - | `List[WebhookConfig]` |
| POST | `/api/webhooks` | Create webhook | `CreateWebhookRequest` | `WebhookConfig` |
| POST | `/api/credentials` | Upload credentials | `UploadCredentialsRequest` | `APIResponse` |
| POST | `/api/env` | Set env vars | `Dict[str, str]` | `APIResponse` |

---

## WebSocket Protocol

### Connection

```
ws://localhost:8080/ws/{session_id}
```

### Server → Client Events

```json
// Task created
{"type": "task.created", "task_id": "...", "agent": "planning", "status": "running"}

// Task output (streaming)
{"type": "task.output", "task_id": "...", "chunk": "Analyzing..."}

// Task metrics update
{"type": "task.metrics", "task_id": "...", "cost_usd": 0.05, "tokens": 1500}

// Task completed
{"type": "task.completed", "task_id": "...", "result": "...", "cost_usd": 0.12}

// Task failed
{"type": "task.failed", "task_id": "...", "error": "..."}
```

### Client → Server Commands

```json
// Send input to task
{"type": "task.input", "task_id": "...", "message": "yes, proceed"}

// Stop task
{"type": "task.stop", "task_id": "..."}

// Chat with Brain
{"type": "chat.message", "message": "Fix the auth bug in login API"}
```

---

## Directory Structure

### Container Layout

```
/app/
├── .claude/
│   └── CLAUDE.md                    # 🧠 Brain instructions (AUTO-UPDATED)
│
├── skills/                          # 🧠 BRAIN SKILLS
│   ├── container-management/
│   │   └── SKILL.md                 # Install packages, manage services
│   │
│   ├── subagent-management/
│   │   └── SKILL.md                 # Spawn, stop, monitor sub-agents
│   │
│   ├── webhook-management/
│   │   └── SKILL.md                 # Create, edit, delete webhooks
│   │
│   └── entity-creation/
│       └── SKILL.md                 # Create new agents, skills
│
├── agents/
│   ├── planning/
│   │   ├── .claude/
│   │   │   └── CLAUDE.md            # Planning agent instructions
│   │   └── skills/                  # 📋 PLANNING AGENT SKILLS
│   │       ├── discovery/SKILL.md
│   │       ├── jira-enrichment/SKILL.md
│   │       └── plan-creation/SKILL.md
│   │
│   ├── executor/
│   │   ├── .claude/
│   │   │   └── CLAUDE.md            # Executor agent instructions
│   │   └── skills/                  # ⚙️ EXECUTOR AGENT SKILLS
│   │       ├── code-implementation/SKILL.md
│   │       ├── tdd-workflow/SKILL.md
│   │       └── pr-management/SKILL.md
│   │
│   └── {custom-agent}/              # 🔧 DYNAMIC AGENTS
│       ├── .claude/CLAUDE.md
│       └── skills/{skill}/SKILL.md
│
└── /data/ (persistent volume)
    ├── db/machine.db                # SQLite database
    ├── config/
    │   ├── webhooks/                # Dynamic webhooks
    │   ├── agents/                  # Dynamic agents
    │   └── skills/                  # Dynamic skills
    └── registry/
        ├── webhooks.yaml            # All webhooks list
        ├── agents.yaml              # All agents + their skills
        └── skills.yaml              # Brain skills list
```

### CLAUDE.md Auto-Update Mechanism

When any webhook, skill, or sub-agent is added, the main `/app/.claude/CLAUDE.md` is **automatically updated** with the new information:

```python
# shared/claude_md_updater.py

from pathlib import Path
from typing import List
import yaml

def update_main_claude_md():
    """Update Brain's CLAUDE.md with current available resources."""
    
    webhooks = _load_registry("webhooks")
    agents = _load_registry("agents")
    skills = _list_brain_skills()
    
    content = f'''# Claude Machine Brain

## Your Role
You are the Brain of this machine. You manage sub-agents and handle user requests.

## Your Skills
{_format_skills(skills)}

## Available Sub-Agents
{_format_agents(agents)}

## Available Webhooks
{_format_webhooks(webhooks)}

## You CAN:
- Spawn sub-agents for tasks using your subagent-management skill
- Edit files in /app/ and /data/
- Run bash commands
- Create new webhooks/agents/skills using entity-creation skill
- Install packages using container-management skill

## You CANNOT:
- Modify /data/credentials/ directly
- Delete system files in /app/.claude/
- Access external APIs without going through sub-agents
'''
    
    Path("/app/.claude/CLAUDE.md").write_text(content)
```

### Brain CLAUDE.md Example

```markdown
# Claude Machine Brain

## Your Role
You are the Brain of this machine. You manage sub-agents and handle user requests.

## Your Skills
| Skill | Path | Description |
|-------|------|-------------|
| container-management | /app/skills/container-management/ | Install packages, manage services |
| subagent-management | /app/skills/subagent-management/ | Spawn, stop, monitor sub-agents |
| webhook-management | /app/skills/webhook-management/ | Create, edit, delete webhooks |
| entity-creation | /app/skills/entity-creation/ | Create new agents and skills |

## Available Sub-Agents
| Agent | Path | Skills |
|-------|------|--------|
| planning | /app/agents/planning/ | discovery, jira-enrichment, plan-creation |
| executor | /app/agents/executor/ | code-implementation, tdd-workflow, pr-management |

## Available Webhooks
| Name | Endpoint | Target Agent |
|------|----------|--------------|
| github | /webhooks/github | planning |
| jira | /webhooks/jira | planning |
| sentry | /webhooks/sentry | planning |
```

### Sub-Agent CLAUDE.md Example (Planning)

```markdown
# Planning Agent

## Your Role
You analyze bugs and create fix plans. You do NOT implement code.

## Your Skills
- /app/agents/planning/skills/discovery/ - Analyze codebase
- /app/agents/planning/skills/jira-enrichment/ - Update Jira tickets
- /app/agents/planning/skills/plan-creation/ - Create PLAN.md files

## You CAN:
- Read code from any repository via MCP GitHub
- Query Sentry for error details via MCP Sentry
- Create PLAN.md files
- Open draft PRs
- Comment on Jira tickets

## You CANNOT:
- Modify actual code (implementation is for Executor)
- Push to main branch
- Approve your own plans
- Access Brain-level skills

## Output Format
Always end with a clear PLAN.md structure.
```

---

## Database Strategy

> [!IMPORTANT]
> **Two databases for different purposes:**
> - **Redis** = Queue + Cache + Real-time (ephemeral)
> - **SQLite** = Persistence + History (permanent)

### Redis (Task Queue + Cache)

```python
# What Redis stores (ephemeral - can be lost):
{
    "task_queue": ["task-001", "task-002"],           # Pending tasks
    "task:{id}:status": "running",                     # Current status
    "task:{id}:pid": "12345",                          # Process ID for stop
    "task:{id}:output": "Analysis in progress...",     # Live output buffer
    "session:{id}:tasks": ["task-001"],                # Active session tasks
}

# Redis connection
REDIS_URL = "redis://redis:6379/0"
```

### SQLite (Persistence)

```python
# What SQLite stores (permanent - survives restarts):
- Sessions history
- Completed tasks with results
- Cost/metrics history
- Webhook configurations
- Agent configurations
- Skill configurations
```

### Why NOT PostgreSQL?

| Criteria | SQLite | PostgreSQL |
|----------|--------|------------|
| Setup complexity | ✅ Zero - single file | ❌ Separate container |
| Persistence | ✅ Volume mount | ✅ Volume mount |
| Concurrent writes | ⚠️ Limited | ✅ High |
| Our use case | ✅ Low write volume | ⚠️ Overkill |

> **Decision**: Start with SQLite. Migrate to PostgreSQL later if needed.

---

## Dashboard Testing

### Frontend Testing Approach

> [!NOTE]
> Dashboard UI is tested via **browser automation** (Playwright) and **API tests**.
> No unit tests for HTML/JS - test the behavior, not the implementation.

```python
# tests/e2e/test_dashboard.py
"""Dashboard end-to-end tests using Playwright."""

import pytest
from playwright.async_api import async_playwright


@pytest.mark.e2e
async def test_dashboard_loads():
    """Dashboard loads without errors."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://localhost:8000")
        
        # Check main elements exist
        assert await page.locator("h1").text_content() == "Claude Machine"
        await browser.close()


@pytest.mark.e2e
async def test_chat_sends_message():
    """Chat input sends message and shows response."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://localhost:8000")
        
        # Type and send message
        await page.fill("#chat-input", "Hello")
        await page.click("#send-button")
        
        # Wait for response
        await page.wait_for_selector(".task-card")
        assert await page.locator(".task-card").count() >= 1
        
        await browser.close()


@pytest.mark.e2e
async def test_task_appears_in_list():
    """Created task appears in active tasks list."""
    # ...


@pytest.mark.e2e
async def test_websocket_receives_updates():
    """WebSocket receives task output updates."""
    # ...
```

### API Tests for Dashboard Backend

```python
# tests/integration/test_dashboard_api.py
"""Dashboard API integration tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_endpoint_creates_task(client: AsyncClient):
    """POST /api/chat creates a task and returns task_id."""
    response = await client.post("/api/chat", json={
        "message": "Fix the bug"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_tasks_endpoint_returns_list(client: AsyncClient):
    """GET /api/tasks returns task list."""
    response = await client.get("/api/tasks")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_websocket_connection(client: AsyncClient):
    """WebSocket connects and receives messages."""
    async with client.websocket_connect("/ws/test-session") as ws:
        # Send a chat message
        await ws.send_json({"type": "chat.message", "message": "Hello"})
        
        # Should receive task.created event
        data = await ws.receive_json()
        assert data["type"] == "task.created"
```

---

## Persistence Layer

### SQLite Schema

```sql
-- Sessions
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    disconnected_at TIMESTAMP,
    total_cost_usd REAL DEFAULT 0.0,
    total_tasks INTEGER DEFAULT 0
);

-- Tasks
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    assigned_agent TEXT,
    agent_type TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    input_message TEXT NOT NULL,
    output_stream TEXT DEFAULT '',
    result TEXT,
    error TEXT,
    cost_usd REAL DEFAULT 0.0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    duration_seconds REAL DEFAULT 0.0,
    source TEXT DEFAULT 'dashboard',
    source_metadata TEXT DEFAULT '{}',
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Dynamic entities (JSON storage for flexibility)
CREATE TABLE entities (
    name TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,  -- 'webhook', 'agent', 'skill'
    config TEXT NOT NULL,       -- JSON serialized Pydantic model
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Development Guidelines

### Commands

```bash
# Always use uv
uv sync               # Install dependencies
uv add <package>      # Add dependency
uv run pytest         # Run tests
uv run mypy .         # Type check
uv run ruff check .   # Lint

# Docker (uses uv internally)
make build            # Build containers
make up               # Start services
make test             # Run tests in container
make logs             # View logs
```

### Code Style

```python
# ALWAYS use Pydantic for data
from shared.machine_models import Task, Session

# NEVER use raw dictionaries for domain data
# BAD:
task = {"task_id": "123", "status": "running"}

# GOOD:
task = Task(task_id="123", status=TaskStatus.RUNNING, ...)

# Use async/await for all I/O
async def process_task(task: Task) -> None:
    ...

# Type everything
def create_agent(config: SubAgentConfig) -> SubAgentConfig:
    ...
```

### Testing

```python
# Test business logic via Pydantic validation
def test_task_cannot_transition_from_completed():
    """Completed tasks cannot transition."""
    task = Task(task_id="t1", session_id="s1", user_id="u1",
                input_message="test", status=TaskStatus.COMPLETED)
    
    assert not task.can_transition_to(TaskStatus.RUNNING)
    
    with pytest.raises(ValueError):
        task.transition_to(TaskStatus.RUNNING)
```

---

## Infrastructure Files

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI
RUN curl -fsSL https://cli.anthropic.com/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /data/db /data/config /data/credentials

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
# docker-compose.yml
version: "3.8"

services:
  app:
    build: .
    container_name: claude-code-agent
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=sqlite:////data/db/machine.db
      - MACHINE_ID=${MACHINE_ID:-claude-agent-001}
      - MAX_CONCURRENT_TASKS=${MAX_CONCURRENT_TASKS:-5}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - machine_data:/data
      - ./agents:/app/agents:ro        # Sub-agent definitions
      - ./skills:/app/skills:ro        # Brain skills
      - ./.claude:/app/.claude:ro      # Main CLAUDE.md
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: claude-agent-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

volumes:
  machine_data:
    driver: local
  redis_data:
    driver: local
```

### pyproject.toml

```toml
# pyproject.toml
[project]
name = "claude-code-agent"
version = "0.1.0"
description = "Claude Code CLI Agent with FastAPI daemon"
requires-python = ">=3.11"
readme = "README.md"

dependencies = [
    # Core
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    
    # Database
    "redis>=5.0.0",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.19.0",
    
    # HTTP
    "httpx>=0.26.0",
    "websockets>=12.0",
    
    # Logging
    "structlog>=24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.8.0",
    "ruff>=0.2.0",
    "playwright>=1.40.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.8.0",
    "ruff>=0.2.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true

[tool.ruff]
line-length = 100
target-version = "py312"
```

### main.py (Entry Point)

```python
# main.py
"""Main entry point for Claude Code Agent."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import structlog

from core.config import settings
from core.database import init_db
from core.redis_client import redis_client
from api import webhooks, dashboard, websocket
from workers.task_worker import TaskWorker


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    logger.info("Starting Claude Code Agent", machine_id=settings.machine_id)
    
    # Initialize database
    await init_db()
    
    # Connect to Redis
    await redis_client.connect()
    
    # Start task worker
    worker = TaskWorker()
    worker_task = asyncio.create_task(worker.run())
    
    # Update CLAUDE.md with current config
    from core.claude_md_updater import update_main_claude_md
    await update_main_claude_md()
    
    logger.info("Claude Code Agent ready", port=8000)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Claude Code Agent")
    worker_task.cancel()
    await redis_client.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Claude Code Agent",
    description="Claude Code CLI Agent with dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(websocket.router, tags=["websocket"])

# Serve static files (dashboard frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Redirect to dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "machine_id": settings.machine_id}
```

---

## Template Files

### Brain CLAUDE.md Template

```markdown
# file: .claude/CLAUDE.md

# Claude Machine Brain

## Your Role
You are the Brain of this machine. You manage sub-agents and handle user requests.

## Your Skills
| Skill | Path | Description |
|-------|------|-------------|
| container-management | /app/skills/container-management/ | Install packages, manage services |
| subagent-management | /app/skills/subagent-management/ | Spawn, stop, monitor sub-agents |
| webhook-management | /app/skills/webhook-management/ | Create, edit, delete webhooks |
| entity-creation | /app/skills/entity-creation/ | Create new agents and skills |

## Available Sub-Agents
| Agent | Path | Skills |
|-------|------|--------|
| planning | /app/agents/planning/ | discovery, jira-enrichment, plan-creation |
| executor | /app/agents/executor/ | code-implementation, tdd-workflow, pr-management |

## Available Webhooks
| Name | Endpoint | Target Agent |
|------|----------|--------------|
| github | /webhooks/github | planning |
| jira | /webhooks/jira | planning |
| sentry | /webhooks/sentry | planning |

## You CAN:
- Spawn sub-agents for tasks using your subagent-management skill
- Edit files in /app/ and /data/
- Run bash commands
- Create new webhooks/agents/skills using entity-creation skill
- Install packages using container-management skill

## You CANNOT:
- Modify /data/credentials/ directly
- Delete system files in /app/.claude/
- Access external APIs without going through sub-agents
```

### Sub-Agent CLAUDE.md Template (Planning)

```markdown
# file: agents/planning/.claude/CLAUDE.md

# Planning Agent

## Your Role
You analyze bugs and create fix plans. You do NOT implement code.

## Your Skills
- /app/agents/planning/skills/discovery/ - Analyze codebase
- /app/agents/planning/skills/jira-enrichment/ - Update Jira tickets
- /app/agents/planning/skills/plan-creation/ - Create PLAN.md files

## You CAN:
- Read code from any repository via MCP GitHub
- Query Sentry for error details via MCP Sentry
- Create PLAN.md files
- Open draft PRs
- Comment on Jira tickets

## You CANNOT:
- Modify actual code (implementation is for Executor)
- Push to main branch
- Approve your own plans
- Access Brain-level skills

## Output Format
Always end with a clear PLAN.md structure.
```

### SKILL.md Template

```markdown
# file: skills/subagent-management/SKILL.md
---
name: subagent-management
description: Spawn, stop, and monitor sub-agents
---

# Sub-Agent Management Skill

## Usage
Use this skill when the user wants to:
- Start a new sub-agent task
- Stop a running sub-agent
- Check status of sub-agents
- List available sub-agents

## Commands

### Spawn Sub-Agent
```bash
# List available agents
ls /app/agents/

# Check agent configuration
cat /app/agents/{agent_name}/.claude/CLAUDE.md

# To spawn, create a task via the API (you cannot spawn directly)
# The worker will spawn the agent subprocess
```

### Stop Sub-Agent
```python
# Send stop signal via API
POST /api/tasks/{task_id}/stop
```

## Available Agents
Read from /data/registry/agents.yaml for current list.
```

---

## Error Handling

### Global Exception Handler

```python
# core/exceptions.py
"""Global exception handling."""

from fastapi import Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


class AgentError(Exception):
    """Base exception for agent errors."""
    def __init__(self, message: str, code: str = "AGENT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class AuthenticationError(AgentError):
    """Claude authentication failed."""
    def __init__(self, message: str = "Claude authentication required"):
        super().__init__(message, "AUTH_ERROR")


class TaskError(AgentError):
    """Task execution error."""
    def __init__(self, message: str, task_id: str):
        self.task_id = task_id
        super().__init__(message, "TASK_ERROR")


class WebhookError(AgentError):
    """Webhook processing error."""
    def __init__(self, message: str, source: str):
        self.source = source
        super().__init__(message, "WEBHOOK_ERROR")


# Exception handlers for FastAPI
async def agent_error_handler(request: Request, exc: AgentError):
    """Handle AgentError exceptions."""
    logger.error("Agent error", code=exc.code, message=exc.message)
    return JSONResponse(
        status_code=400,
        content={"error": exc.code, "message": exc.message}
    )


async def auth_error_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors."""
    logger.warning("Authentication required", message=exc.message)
    return JSONResponse(
        status_code=401,
        content={
            "error": "AUTH_REQUIRED",
            "message": exc.message,
            "action": "Upload credentials via dashboard"
        }
    )


# Register handlers in main.py:
# app.add_exception_handler(AgentError, agent_error_handler)
# app.add_exception_handler(AuthenticationError, auth_error_handler)
```

---

## Logging Configuration

### Structured Logging Setup

```python
# core/logging.py
"""Structured logging configuration."""

import sys
import structlog
from pydantic import BaseModel


def setup_logging(log_level: str = "INFO", json_format: bool = True):
    """Configure structured logging."""
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, log_level.upper(), structlog.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Log format example:
# {"timestamp": "2026-01-21T22:00:00Z", "level": "info", "event": "Task started", "task_id": "abc123"}
```

### Logging Usage

```python
# In any module
import structlog

logger = structlog.get_logger()

async def process_task(task_id: str):
    logger.info("Processing task", task_id=task_id)
    
    try:
        result = await execute_task(task_id)
        logger.info("Task completed", task_id=task_id, cost=result.cost_usd)
    except Exception as e:
        logger.error("Task failed", task_id=task_id, error=str(e))
        raise
```

---

## Dashboard Frontend

### index.html

```html
<!-- static/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Machine Dashboard</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div id="app">
        <!-- Header -->
        <header class="header">
            <h1>🤖 Claude Machine Dashboard</h1>
            <div class="user-info">
                <span id="machine-status" class="status-badge">●</span>
                <span id="user-email">loading...</span>
            </div>
        </header>
        
        <!-- Main Content -->
        <main class="main-content">
            <!-- Status Panel -->
            <section class="panel status-panel">
                <h2>Machine Status</h2>
                <div class="stats">
                    <div class="stat">
                        <span class="label">Machine ID</span>
                        <span id="machine-id" class="value">-</span>
                    </div>
                    <div class="stat">
                        <span class="label">Active Tasks</span>
                        <span id="active-tasks" class="value">0</span>
                    </div>
                    <div class="stat">
                        <span class="label">Session Cost</span>
                        <span id="session-cost" class="value">$0.00</span>
                    </div>
                </div>
            </section>
            
            <!-- Active Tasks -->
            <section class="panel tasks-panel">
                <h2>Active Tasks</h2>
                <div id="tasks-list" class="tasks-list">
                    <!-- Tasks will be populated by JavaScript -->
                </div>
            </section>
            
            <!-- Chat Panel -->
            <section class="panel chat-panel">
                <h2>Chat with Machine</h2>
                <div id="chat-messages" class="chat-messages">
                    <!-- Messages will be populated by JavaScript -->
                </div>
                <div class="chat-input">
                    <input type="text" id="chat-input" placeholder="Type a message...">
                    <button id="send-button">Send</button>
                </div>
            </section>
            
            <!-- Quick Actions -->
            <section class="panel actions-panel">
                <h2>Quick Actions</h2>
                <div class="actions">
                    <button onclick="showModal('webhook')">+ Add Webhook</button>
                    <button onclick="showModal('agent')">+ Add Agent</button>
                    <button onclick="showModal('skill')">+ Add Skill</button>
                    <button onclick="showModal('settings')">⚙️ Settings</button>
                </div>
            </section>
        </main>
    </div>
    
    <!-- Modal -->
    <div id="modal" class="modal hidden">
        <div class="modal-content">
            <span class="close" onclick="hideModal()">&times;</span>
            <div id="modal-body"></div>
        </div>
    </div>
    
    <script src="/static/js/app.js"></script>
</body>
</html>
```

### WebSocket Client (JavaScript)

```javascript
// static/js/app.js

class DashboardApp {
    constructor() {
        this.ws = null;
        this.sessionId = this.generateSessionId();
        this.tasks = new Map();
        
        this.init();
    }
    
    generateSessionId() {
        return 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }
    
    async init() {
        await this.loadStatus();
        this.connectWebSocket();
        this.setupEventListeners();
    }
    
    async loadStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            document.getElementById('machine-id').textContent = data.machine_id;
            document.getElementById('machine-status').classList.add('online');
        } catch (error) {
            console.error('Failed to load status:', error);
            document.getElementById('machine-status').classList.add('offline');
        }
    }
    
    connectWebSocket() {
        const wsUrl = `ws://${window.location.host}/ws/${this.sessionId}`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
        };
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected, reconnecting...');
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    handleMessage(message) {
        switch (message.type) {
            case 'task.created':
                this.addTask(message);
                break;
            case 'task.output':
                this.updateTaskOutput(message.task_id, message.chunk);
                break;
            case 'task.metrics':
                this.updateTaskMetrics(message.task_id, message);
                break;
            case 'task.completed':
                this.completeTask(message.task_id, message.result);
                break;
            case 'task.failed':
                this.failTask(message.task_id, message.error);
                break;
        }
    }
    
    addTask(data) {
        this.tasks.set(data.task_id, {
            id: data.task_id,
            agent: data.agent,
            status: data.status,
            output: '',
            cost: 0
        });
        this.renderTasks();
    }
    
    updateTaskOutput(taskId, chunk) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.output += chunk;
            this.renderTaskOutput(taskId);
        }
    }
    
    updateTaskMetrics(taskId, metrics) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.cost = metrics.cost_usd;
            this.renderTasks();
        }
    }
    
    completeTask(taskId, result) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.status = 'completed';
            task.result = result;
            this.renderTasks();
        }
    }
    
    failTask(taskId, error) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.status = 'failed';
            task.error = error;
            this.renderTasks();
        }
    }
    
    renderTasks() {
        const container = document.getElementById('tasks-list');
        container.innerHTML = '';
        
        for (const [taskId, task] of this.tasks) {
            const el = document.createElement('div');
            el.className = `task-card status-${task.status}`;
            el.innerHTML = `
                <div class="task-header">
                    <span class="task-id">${taskId}</span>
                    <span class="task-agent">${task.agent}</span>
                    <span class="task-cost">$${task.cost.toFixed(2)}</span>
                </div>
                <div class="task-status">${task.status}</div>
                <div class="task-actions">
                    <button onclick="app.viewTask('${taskId}')">View</button>
                    <button onclick="app.stopTask('${taskId}')">Stop</button>
                </div>
            `;
            container.appendChild(el);
        }
    }
    
    renderTaskOutput(taskId) {
        // Update task output view if visible
        const outputEl = document.getElementById(`task-output-${taskId}`);
        if (outputEl) {
            const task = this.tasks.get(taskId);
            outputEl.textContent = task.output;
        }
    }
    
    setupEventListeners() {
        // Send button
        document.getElementById('send-button').onclick = () => this.sendMessage();
        
        // Enter key
        document.getElementById('chat-input').onkeypress = (e) => {
            if (e.key === 'Enter') this.sendMessage();
        };
    }
    
    sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (message && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'chat.message',
                message: message
            }));
            
            // Add to chat display
            this.addChatMessage('user', message);
            input.value = '';
        }
    }
    
    addChatMessage(role, content) {
        const container = document.getElementById('chat-messages');
        const el = document.createElement('div');
        el.className = `chat-message ${role}`;
        el.textContent = content;
        container.appendChild(el);
        container.scrollTop = container.scrollHeight;
    }
    
    async stopTask(taskId) {
        try {
            await fetch(`/api/tasks/${taskId}/stop`, { method: 'POST' });
        } catch (error) {
            console.error('Failed to stop task:', error);
        }
    }
    
    viewTask(taskId) {
        // Show task detail modal
        const task = this.tasks.get(taskId);
        if (task) {
            document.getElementById('modal-body').innerHTML = `
                <h3>Task: ${taskId}</h3>
                <p>Agent: ${task.agent}</p>
                <p>Status: ${task.status}</p>
                <p>Cost: $${task.cost.toFixed(4)}</p>
                <div class="task-output" id="task-output-${taskId}">${task.output}</div>
            `;
            document.getElementById('modal').classList.remove('hidden');
        }
    }
}

// Modal functions
function showModal(type) {
    document.getElementById('modal').classList.remove('hidden');
    // Load appropriate content based on type
}

function hideModal() {
    document.getElementById('modal').classList.add('hidden');
}

// Initialize app
const app = new DashboardApp();
```

---

## Test Files Structure

```
tests/
├── conftest.py                    # Pytest fixtures
├── unit/
│   ├── test_models.py             # Pydantic model tests
│   ├── test_brain_routing.py      # Brain routing logic
│   ├── test_command_parser.py     # Webhook command parsing
│   └── test_task_transitions.py   # Task state machine
├── integration/
│   ├── test_api_endpoints.py      # FastAPI endpoint tests
│   ├── test_websocket.py          # WebSocket tests
│   ├── test_cli_runner.py         # Claude CLI execution
│   └── test_redis_queue.py        # Redis queue operations
└── e2e/
    ├── test_dashboard.py          # Playwright browser tests
    ├── test_webhook_flow.py       # Full webhook → task flow
    └── test_chat_flow.py          # Full chat → response flow
```

### conftest.py

```python
# tests/conftest.py
"""Pytest fixtures for all tests."""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from main import app
from core.database import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """Create async HTTP client for API tests."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def db_session():
    """Create test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session


@pytest.fixture
def sample_task():
    """Create sample task for testing."""
    from core.models import Task, TaskStatus
    return Task(
        task_id="test-001",
        session_id="session-001",
        user_id="user-001",
        input_message="Fix the bug",
        status=TaskStatus.QUEUED,
    )
```

---

*Created: 2026-01-21*  
*Author: Claude Machine System*
