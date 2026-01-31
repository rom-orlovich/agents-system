# Agent Engine Package

> Core Python package containing agents, skills, CLI providers, and task management for the agent-bot system.

## Package Overview

This is the **heart of the agent-bot system** - a reusable Python package that provides:
- Multi-CLI provider support (Claude Code, Cursor)
- 7 specialized agents for different workflows
- 9 reusable skills for common operations
- Redis-based task queue management
- SQLAlchemy models for persistence

## Installation

```bash
# Development install
pip install -e ".[dev]"

# Production install
pip install agent-engine
```

## Package Structure

```
agent_engine/
├── __init__.py
├── core/
│   ├── config.py              # Settings (Pydantic)
│   ├── queue_manager.py       # Redis task queue
│   ├── worker.py              # TaskWorker with semaphore
│   └── cli/
│       ├── base.py            # CLIProvider protocol, CLIResult
│       ├── executor.py        # Provider factory
│       ├── sanitization.py    # Sensitive data filtering
│       └── providers/
│           ├── claude/
│           │   ├── config.py  # Claude CLI configuration
│           │   └── runner.py  # Subprocess execution
│           └── cursor/
│               ├── config.py  # Cursor CLI configuration
│               └── runner.py  # Subprocess execution
├── agents/
│   ├── base.py                # BaseAgent ABC, AgentContext
│   ├── brain.py               # Central orchestrator
│   ├── executor.py            # TDD implementation
│   ├── planning.py            # Discovery + planning
│   ├── verifier.py            # Quality verification
│   ├── github_issue_handler.py
│   ├── github_pr_review.py
│   ├── jira_code_plan.py
│   └── slack_inquiry.py
├── skills/
│   ├── base.py                # BaseSkill ABC
│   ├── discovery.py
│   ├── testing.py
│   ├── code_refactoring.py
│   ├── github_operations.py
│   ├── jira_operations.py
│   ├── slack_operations.py
│   ├── human_approval.py
│   └── verification.py
├── models/
│   ├── base.py                # SQLAlchemy base
│   ├── task.py                # Task, AgentExecution
│   └── conversation.py        # Conversation threading
└── memory/
    └── __init__.py            # Self-improvement hooks
```

## CLI Provider System

### Protocol Interface

```python
@runtime_checkable
class CLIProvider(Protocol):
    async def run(
        self,
        prompt: str,
        working_dir: Path,
        output_queue: asyncio.Queue[str | None],
        task_id: str = "",
        timeout_seconds: int = 3600,
        model: str | None = None,
        allowed_tools: str | None = None,
    ) -> CLIResult: ...
```

### CLIResult Dataclass

```python
@dataclass(frozen=True)
class CLIResult:
    success: bool
    output: str
    clean_output: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    error: str | None
```

### Provider Selection

```python
from agent_engine.core.cli.executor import CLIExecutor

executor = CLIExecutor(provider_type="claude")  # or "cursor"
result = await executor.run(prompt, working_dir, output_queue)
```

## Agent System

### Base Agent

All agents inherit from `BaseAgent`:

```python
class BaseAgent(ABC):
    agent_type: AgentType

    @abstractmethod
    def can_handle(self, context: AgentContext) -> bool: ...

    @abstractmethod
    async def process(self, context: AgentContext) -> AgentResult: ...
```

### Agent Types

| Type | Purpose | Model |
|------|---------|-------|
| `BRAIN` | Task routing orchestrator | opus |
| `PLANNING` | Discovery + PLAN.md | opus |
| `EXECUTOR` | TDD implementation | sonnet |
| `VERIFIER` | Quality verification | opus |
| `GITHUB_ISSUE` | GitHub issue handling | sonnet |
| `GITHUB_PR` | PR review handling | sonnet |
| `JIRA_CODE` | Jira ticket handling | sonnet |
| `SLACK_INQUIRY` | Slack responses | sonnet |

### AgentContext

```python
@dataclass
class AgentContext:
    task_id: str
    source: TaskSource
    event_type: str
    payload: dict[str, Any]
    repository: str | None
    metadata: dict[str, Any]
```

### AgentResult

```python
@dataclass
class AgentResult:
    success: bool
    output: str
    agent_type: AgentType
    next_agent: AgentType | None
    artifacts: dict[str, Any]
    should_respond: bool
    response_channel: str | None
```

## Task Queue Management

### QueueManager

```python
from agent_engine.core.queue_manager import QueueManager, TaskStatus

manager = QueueManager(redis_url="redis://localhost:6379/0")

# Push task
await manager.push_task(task_data)

# Pop task (blocking)
task = await manager.pop_task(timeout=5)

# Update status
await manager.set_task_status(task_id, TaskStatus.RUNNING)

# Append output (streaming)
await manager.append_output(task_id, "chunk of output")

# Get full output
output = await manager.get_output(task_id)
```

### TaskStatus Enum

```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

## Configuration

### Settings

```python
from agent_engine.core.config import settings

# CLI Provider
settings.cli_provider  # CLIProviderType.CLAUDE

# Concurrency
settings.max_concurrent_tasks  # 5
settings.task_timeout_seconds  # 3600

# Model Selection
settings.get_model_for_agent("planning")  # "claude-opus-4-5-20251101"
settings.get_model_for_agent("executor")  # "claude-sonnet-4-5-20250929"
```

### Environment Variables

```bash
CLI_PROVIDER=claude              # or 'cursor'
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT_SECONDS=3600
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
```

## Testing

### Run Tests

```bash
# All tests
python -m pytest -v

# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# With coverage
python -m pytest --cov=agent_engine --cov-report=html
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_config.py       # Settings tests
│   ├── test_queue_manager.py # Queue tests
│   ├── test_cli_base.py     # CLI protocol tests
│   └── test_sanitization.py # Sanitization tests
└── integration/
    ├── test_agent_engine.py # Full agent tests
    ├── test_e2e_workflow.py # End-to-end tests
    └── test_webhook_flow.py # Webhook tests
```

### Key Fixtures

```python
@pytest.fixture
def mock_redis() -> AsyncMock:
    """Mocked Redis client"""

@pytest.fixture
def mock_cli_process() -> MagicMock:
    """Mocked subprocess"""

@pytest.fixture
def sample_github_task() -> dict[str, Any]:
    """Sample GitHub webhook payload"""
```

## Code Quality

### Linting

```bash
ruff check .          # Check issues
ruff check . --fix    # Auto-fix
ruff format .         # Format code
```

### Type Checking

```bash
mypy . --strict
```

### File Size Limit

Maximum 300 lines per file. Check with:

```bash
find . -name "*.py" -exec wc -l {} \; | awk '$1 > 300'
```

## Development Rules

1. **NO `any` types** - Use explicit types always
2. **NO comments** - Self-explanatory code only
3. **Async I/O** - Use `httpx.AsyncClient`, not `requests`
4. **Structured logging** - `logger.info("event", key=value)`
5. **TDD approach** - Write tests first

## Key Files

| File | Purpose |
|------|---------|
| `core/config.py` | Central settings and configuration |
| `core/queue_manager.py` | Redis task queue operations |
| `core/cli/base.py` | CLI provider protocol and result |
| `core/cli/providers/claude/runner.py` | Claude CLI subprocess execution |
| `agents/base.py` | Base agent class and types |
| `agents/brain.py` | Task routing orchestrator |
| `skills/base.py` | Base skill class and types |
| `models/task.py` | Task and execution SQLAlchemy models |

## Extending the System

### Adding a New Agent

1. Create `agents/my_agent.py`
2. Inherit from `BaseAgent`
3. Implement `can_handle()` and `process()`
4. Add to `AgentType` enum
5. Register in brain router

### Adding a New Skill

1. Create `skills/my_skill.py`
2. Inherit from `BaseSkill`
3. Implement `get_available_actions()` and `execute()`
4. Add to `SkillType` enum

### Adding a New CLI Provider

1. Create `core/cli/providers/my_cli/`
2. Add `config.py` with provider settings
3. Add `runner.py` implementing `CLIProvider` protocol
4. Register in `CLIExecutor` factory
