# Code Quality Standards

## Core Principles

### 1. Strict Type Safety

**NO `Any` types**:

```python
# ❌ BAD
def process_data(data: Any) -> Any:
    return data.get("value")

# ✅ GOOD
def process_data(data: dict[str, str | int]) -> str | int | None:
    if "value" not in data:
        return None
    return data["value"]
```

**NO `!!` (force unwrapping)**:

```python
# ❌ BAD
result = optional_value!!.process()

# ✅ GOOD
if optional_value is not None:
    result = optional_value.process()
else:
    raise ValueError("optional_value is required")
```

**Explicit Optional Handling**:

```python
# ❌ BAD
def get_user(user_id: str) -> User:
    user = db.find_user(user_id)
    return user  # What if user is None?

# ✅ GOOD
def get_user(user_id: str) -> User | None:
    return db.find_user(user_id)

def require_user(user_id: str) -> User:
    user = db.find_user(user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")
    return user
```

**Type Guards**:

```python
# ✅ GOOD
def process_optional_value(value: str | None) -> str:
    if value is None:
        raise ValueError("value is required")
    return value.upper()
```

---

### 2. Self-Explanatory Code (NO Comments)

**Code must be self-explanatory through**:

- Clear, descriptive names
- Well-structured organization
- Explicit type annotations
- Clear logic flow

```python
# ❌ BAD
def proc(d):  # Process data
    # Check if valid
    if d:
        # Return processed
        return d.upper()
    # Return empty
    return ""

# ✅ GOOD
def process_user_input(user_input: str) -> str:
    if not user_input:
        return ""
    return user_input.upper()
```

```python
# ❌ BAD
# Calculate total cost
total = sum(costs)

# ✅ GOOD
total_cost_usd = sum(task_costs)

# ❌ BAD
# This function validates the webhook signature
def validate(sig, payload):
    ...

# ✅ GOOD
def validate_webhook_signature(
    signature: str,
    payload: bytes,
    secret: str
) -> bool:
    ...
```

---

### 3. Modular Design

**Single Responsibility Principle**:

```python
# ❌ BAD - Does too much
class WebhookProcessor:
    def process(self, webhook):
        # Validate
        # Parse
        # Create task
        # Send response
        # Log
        ...

# ✅ GOOD - Single responsibility
class WebhookValidator:
    def validate(self, webhook: WebhookPayload) -> bool:
        ...

class WebhookParser:
    def parse(self, payload: dict) -> ParsedWebhook:
        ...

class TaskCreator:
    def create_task(self, parsed: ParsedWebhook) -> Task:
        ...

class WebhookProcessor:
    def __init__(
        self,
        validator: WebhookValidator,
        parser: WebhookParser,
        task_creator: TaskCreator
    ):
        self.validator = validator
        self.parser = parser
        self.task_creator = task_creator

    def process(self, webhook: WebhookPayload) -> ProcessingResult:
        if not self.validator.validate(webhook):
            return ProcessingResult.invalid()

        parsed = self.parser.parse(webhook.payload)
        task = self.task_creator.create_task(parsed)
        return ProcessingResult.success(task)
```

**Interface-Based Design**:

```python
# ✅ GOOD - Protocol for extensibility
from typing import Protocol

class CLIRunner(Protocol):
    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> CLIResult:
        ...

class ClaudeCLIRunner:
    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> CLIResult:
        ...

class CustomCLIRunner:
    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> CLIResult:
        ...
```

---

### 4. TDD for Business Logic

**Test-Driven Development Process**:

1. **RED**: Write failing test
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Improve code while keeping tests green

**Example - Webhook Flow Testing**:

```python
# tests/test_webhook_flow.py

@pytest.mark.asyncio
async def test_github_webhook_complete_flow():
    """Test complete GitHub webhook processing flow"""
    client = AsyncClient(base_url="http://test")

    webhook_payload = create_github_webhook_payload(
        action="created",
        issue_number=42,
        comment="@agent analyze this issue"
    )

    response = await client.post(
        "/webhooks/github",
        json=webhook_payload,
        headers=create_github_headers()
    )

    assert response.status_code == 200

    response_data = response.json()
    assert response_data["success"] is True

    task_id = response_data["task_id"]
    assert task_id is not None

    task = await get_task_from_database(task_id)
    assert task.status == TaskStatus.QUEUED
    assert task.assigned_agent == "planning"
    assert task.input_message == "analyze this issue"

    webhook_logs = await get_webhook_logs(task_id)
    assert webhook_logs.has_stage("received")
    assert webhook_logs.has_stage("validation")
    assert webhook_logs.has_stage("command_matching")
    assert webhook_logs.has_stage("task_created")
    assert webhook_logs.has_stage("queue_push")

@pytest.mark.asyncio
async def test_webhook_invalid_signature_rejected():
    """Test webhook with invalid signature is rejected"""
    ...

@pytest.mark.asyncio
async def test_webhook_no_command_match_returns_200():
    """Test webhook with no matching command returns 200 but no task"""
    ...

@pytest.mark.asyncio
async def test_webhook_error_handling():
    """Test webhook error scenarios are handled gracefully"""
    ...
```

---

### 5. Production-Ready Code

**Error Handling**:

```python
# ❌ BAD
def process_task(task_id: str):
    task = db.get_task(task_id)
    result = cli.run(task.prompt)
    db.save_result(result)

# ✅ GOOD
async def process_task(task_id: str) -> ProcessingResult:
    task = await db.get_task(task_id)
    if task is None:
        return ProcessingResult.error(f"Task {task_id} not found")

    try:
        result = await cli_runner.execute(
            prompt=task.input_message,
            working_dir=task.working_dir,
            model=task.model,
            agents=task.assigned_agents
        )
        await db.save_result(task_id, result)
        return ProcessingResult.success(result)
    except CLIExecutionError as e:
        logger.error("cli_execution_failed", task_id=task_id, error=str(e))
        await db.mark_task_failed(task_id, str(e))
        return ProcessingResult.error(str(e))
```

**Resource Management**:

```python
# ✅ GOOD - Proper async context management
async def process_webhook(webhook: WebhookPayload) -> WebhookResponse:
    async with get_db_session() as session:
        async with get_redis_client() as redis:
            return await process_webhook_with_resources(
                webhook=webhook,
                db_session=session,
                redis_client=redis
            )
```

**Input Validation**:

```python
# ✅ GOOD - Pydantic validation
from pydantic import BaseModel, Field, ConfigDict

class WebhookPayload(BaseModel):
    model_config = ConfigDict(strict=True)

    action: str = Field(..., min_length=1)
    repository: RepositoryInfo = Field(...)
    issue: IssueInfo | None = Field(None)

class WebhookRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    payload: WebhookPayload = Field(...)
    signature: str = Field(..., min_length=1)
    headers: dict[str, str] = Field(...)
```

---

## Checklist for Code Review

### Type Safety

- [ ] No `Any` types
- [ ] No `!!` (force unwrapping)
- [ ] All optional values handled explicitly
- [ ] Type guards used where needed
- [ ] Return types explicit

### Code Quality

- [ ] No comments (code is self-explanatory)
- [ ] Clear, descriptive names
- [ ] Well-structured organization
- [ ] Single Responsibility Principle
- [ ] Modular and extensible

### Testing

- [ ] Tests written FIRST (TDD)
- [ ] Business logic fully tested
- [ ] Webhook flows tested end-to-end
- [ ] Error scenarios tested
- [ ] Edge cases covered

### Production Readiness

- [ ] Proper error handling
- [ ] Resource management (async context managers)
- [ ] Input validation (Pydantic)
- [ ] Logging for debugging
- [ ] No placeholders or TODOs

---

## Examples

### Good Example: Modular CLI Runner

```python
from typing import Protocol
from pydantic import BaseModel

class CLIResult(BaseModel):
    success: bool
    output: str
    error: str | None
    cost_usd: float
    input_tokens: int
    output_tokens: int

class CLIRunner(Protocol):
    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> CLIResult:
        ...

class ClaudeCLIRunner:
    def __init__(self, cli_path: str = "claude"):
        self.cli_path = cli_path

    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> CLIResult:
        command = self._build_command(prompt, working_dir, model, agents)
        process_result = await self._run_command(command, working_dir)
        return self._parse_result(process_result)

    def _build_command(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str]
    ) -> list[str]:
        command = [self.cli_path, "run"]
        command.extend(["--model", model])
        command.extend(["--agents", ",".join(agents)])
        command.extend(["--dir", working_dir])
        command.append(prompt)
        return command

    async def _run_command(
        self,
        command: list[str],
        working_dir: str
    ) -> subprocess.CompletedProcess:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return subprocess.CompletedProcess(
            args=command,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr
        )

    def _parse_result(
        self,
        result: subprocess.CompletedProcess
    ) -> CLIResult:
        if result.returncode != 0:
            return CLIResult(
                success=False,
                output="",
                error=result.stderr.decode(),
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0
            )

        output = result.stdout.decode()
        metrics = self._extract_metrics(output)

        return CLIResult(
            success=True,
            output=output,
            error=None,
            cost_usd=metrics.cost_usd,
            input_tokens=metrics.input_tokens,
            output_tokens=metrics.output_tokens
        )

    def _extract_metrics(self, output: str) -> CLIMetrics:
        ...
```

### Good Example: Webhook Processing

```python
from pydantic import BaseModel, Field, ConfigDict

class WebhookPayload(BaseModel):
    model_config = ConfigDict(strict=True)
    action: str = Field(..., min_length=1)
    repository: dict[str, str] = Field(...)
    issue: dict[str, str | int] | None = Field(None)

class WebhookProcessingResult(BaseModel):
    model_config = ConfigDict(strict=True)
    success: bool
    task_id: str | None = Field(None)
    error: str | None = Field(None)

class WebhookProcessor:
    def __init__(
        self,
        validator: WebhookValidator,
        parser: WebhookParser,
        task_creator: TaskCreator,
        queue: TaskQueue
    ):
        self.validator = validator
        self.parser = parser
        self.task_creator = task_creator
        self.queue = queue

    async def process(
        self,
        payload: dict[str, str | int | dict],
        signature: str,
        provider: str
    ) -> WebhookProcessingResult:
        webhook = WebhookPayload.model_validate(payload)

        if not await self.validator.validate(webhook, signature, provider):
            return WebhookProcessingResult(
                success=False,
                task_id=None,
                error="Invalid signature"
            )

        parsed = self.parser.parse(webhook, provider)

        if parsed.command is None:
            return WebhookProcessingResult(
                success=True,
                task_id=None,
                error=None
            )

        task = await self.task_creator.create_task(parsed)
        await self.queue.enqueue(task.task_id)

        return WebhookProcessingResult(
            success=True,
            task_id=task.task_id,
            error=None
        )
```
