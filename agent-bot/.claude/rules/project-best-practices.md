# Project Best Practices - STRICT RULES

## File Size Limits

**CRITICAL**: Maximum 300 lines per file

### Enforcement
- ❌ NO file should exceed 300 lines
- ✅ Split files into logical modules when approaching limit
- ✅ Use separation of concerns

### How to Split Files

When a file exceeds 300 lines, split into:

```
module/
├── __init__.py         # Public API exports
├── constants.py        # Constants, enums, configs
├── models.py           # Pydantic models, dataclasses
├── exceptions.py       # Custom exceptions
├── utils.py            # Helper functions
├── core.py             # Main logic
└── types.py            # Type definitions
```

### Examples

**Bad**:
```python
# client.py (500 lines) ❌
class JiraClient:
    # 500 lines of code
```

**Good**:
```python
# constants.py
BASE_URL = "https://api.atlassian.net"
DEFAULT_TIMEOUT = 30

# models.py
class AddCommentInput(BaseModel):
    issue_key: str
    comment: str

# exceptions.py
class JiraClientError(Exception):
    pass

# client.py (< 300 lines) ✅
from .constants import BASE_URL
from .models import AddCommentInput
from .exceptions import JiraClientError

class JiraClient:
    # Core logic only
```

## Type Safety

### ABSOLUTE REQUIREMENTS
- ❌ NO `any` types EVER
- ✅ ALWAYS use `ConfigDict(strict=True)` in Pydantic models
- ✅ Use explicit types for all function signatures
- ✅ Use `Literal` for enums

### Examples

**Bad**:
```python
def process(data: Any) -> dict:  ❌
    return data

class Model(BaseModel):  ❌
    value: Any
```

**Good**:
```python
def process(data: Dict[str, str]) -> ProcessResult:  ✅
    return ProcessResult(data=data)

class Model(BaseModel):  ✅
    model_config = ConfigDict(strict=True)
    value: str
    status: Literal["pending", "completed", "failed"]
```

## Code Style

### NO Comments in Code
- ✅ Code must be self-explanatory
- ✅ Use descriptive variable/function names
- ✅ Extract complex logic into named functions
- ❌ NO inline comments explaining "what" code does
- ✅ Only docstrings for public APIs

**Bad**:
```python
# Check if user is authorized ❌
if u.role in ["admin", "superuser"]:
    # Process the request ❌
    r = process(req)
```

**Good**:
```python
def is_authorized(user: User) -> bool:  ✅
    authorized_roles = [UserRole.ADMIN, UserRole.SUPERUSER]
    return user.role in authorized_roles

if is_authorized(user):
    result = process_request(request)
```

## Testing

### Requirements
- ✅ Tests MUST pass gracefully
- ✅ Tests MUST run fast (< 5 seconds per test file)
- ✅ NO flaky tests
- ✅ Use mocks for external dependencies
- ✅ 100% type coverage

### Test Structure

```python
import pytest
from unittest.mock import AsyncMock
from mymodule import MyClass

@pytest.fixture
def mock_client():
    return AsyncMock()

@pytest.mark.asyncio
async def test_success_case(mock_client):
    result = await MyClass(mock_client).execute()
    assert result.success is True

@pytest.mark.asyncio
async def test_failure_case(mock_client):
    mock_client.call.side_effect = Exception("Error")
    with pytest.raises(MyException):
        await MyClass(mock_client).execute()
```

### Test Speed
- ✅ Use `respx` for HTTP mocking (fast)
- ✅ Use `AsyncMock` for async functions
- ❌ NO real network calls
- ❌ NO time.sleep() in tests
- ✅ Use `pytest-asyncio` for async tests

## Architecture

### Separation of Concerns
```
integrations/
├── packages/              # Shared API clients ONLY
│   └── jira_client/
│       ├── __init__.py
│       ├── client.py      # < 300 lines
│       ├── models.py      # < 300 lines
│       ├── exceptions.py  # < 300 lines
│       └── constants.py   # < 300 lines
├── mcp-servers/           # MCP servers ONLY
│   └── jira/
│       ├── __init__.py
│       └── server.py      # < 300 lines
└── api/                   # REST APIs ONLY
    └── jira/
        ├── __init__.py
        └── routes.py      # < 300 lines
```

### DRY Principle
- ✅ Shared clients in `integrations/packages/`
- ✅ MCP servers depend on shared clients
- ✅ REST APIs depend on shared clients
- ❌ NO code duplication between MCP and REST

## Error Handling

### Custom Exceptions
```python
class MyServiceError(Exception):
    """Base exception for MyService."""
    pass

class MyServiceAuthenticationError(MyServiceError):
    """Authentication failed."""
    pass

class MyServiceNotFoundError(MyServiceError):
    """Resource not found."""
    pass
```

### Usage
```python
try:
    result = await client.fetch()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        raise MyServiceAuthenticationError("Invalid credentials")
    elif e.response.status_code == 404:
        raise MyServiceNotFoundError(f"Resource {id} not found")
    else:
        raise MyServiceError(f"HTTP error: {e}")
```

## Logging

### Structured Logging ONLY
```python
import structlog

logger = structlog.get_logger()

# Good ✅
logger.info("task_started", task_id=task_id, user_id=user_id)
logger.error("api_call_failed", service="jira", error=str(e))

# Bad ❌
logger.info(f"Task {task_id} started for user {user_id}")
logger.error(f"API call to jira failed: {e}")
```

## Async/Await

### Requirements
- ✅ ALWAYS use async/await for I/O operations
- ✅ Use `asyncio.gather()` for parallel operations
- ❌ NO sync code in async functions
- ✅ Use `httpx.AsyncClient` not `requests`

```python
# Good ✅
async def fetch_multiple(urls: list[str]) -> list[str]:
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.text for r in responses]

# Bad ❌
def fetch_multiple(urls: list[str]) -> list[str]:
    return [requests.get(url).text for url in urls]
```

## Imports

### Order
1. Standard library
2. Third-party packages
3. Local modules

```python
import asyncio
import json
from typing import Dict, Any

import httpx
import structlog
from pydantic import BaseModel

from .models import MyModel
from .exceptions import MyError
```

## Git Commits

### Commit Message Format
```
<type>: <short description>

<detailed description>

<list of changes>

https://claude.ai/code/session_<session_id>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `test`: Add/update tests
- `docs`: Documentation only
- `chore`: Maintenance

## Performance

### Requirements
- ✅ Connection pooling for HTTP clients
- ✅ Async I/O for all network calls
- ✅ Redis for caching when appropriate
- ❌ NO synchronous blocking calls
- ✅ Use `asyncio.Semaphore` for rate limiting

## Security

### Requirements
- ✅ HMAC signature validation for webhooks
- ✅ Secrets via environment variables ONLY
- ❌ NO hardcoded secrets
- ✅ Use prepared statements for SQL
- ✅ Validate all user inputs with Pydantic

## Documentation

### README Requirements
Each package/module MUST have:
- ✅ Purpose statement
- ✅ Installation instructions
- ✅ Usage examples
- ✅ Testing instructions
- ✅ Dependencies list

### API Documentation
- ✅ Pydantic models serve as schema documentation
- ✅ FastAPI automatically generates OpenAPI docs
- ✅ MCP servers document tools via `list_tools()`

## Summary Checklist

Before committing:
- [ ] All files < 300 lines
- [ ] NO `any` types
- [ ] NO comments in code
- [ ] All tests pass gracefully
- [ ] Tests run fast (< 5s per file)
- [ ] Structured logging used
- [ ] Async/await for I/O
- [ ] NO hardcoded secrets
- [ ] README updated
- [ ] Types are explicit

**If ANY item fails, DO NOT COMMIT!**
