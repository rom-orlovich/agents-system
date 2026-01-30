# Jira Client - Claude Configuration

## Component Overview

Shared Jira API client package. Single source of truth for all Jira operations.

## Purpose

- 🔧 Shared library for Jira API interactions
- ✅ Used by jira_mcp_server (MCP interface)
- ✅ Used by jira_rest_api (HTTP interface)
- 🛡️ Type-safe with strict Pydantic validation
- 🔄 DRY principle - ONE implementation

## Key Rules

### File Size
- ❌ NO file > 300 lines
- ✅ Already split: client.py, models.py, exceptions.py

### Type Safety
- ❌ NO `any` types EVER
- ✅ `ConfigDict(strict=True)` in ALL models
- ✅ Explicit types everywhere

### Code Style
- ❌ NO comments in code
- ✅ Self-explanatory function names
- ✅ Structured logging

## Directory Structure

```
jira_client/
├── jira_client/
│   ├── __init__.py      # Public API exports
│   ├── client.py        # JiraClient class (< 300 lines)
│   ├── models.py        # Pydantic models (< 300 lines)
│   ├── exceptions.py    # Custom exceptions (< 300 lines)
│   └── constants.py     # Constants (if needed)
├── tests/
│   ├── test_client.py   # Client tests
│   └── conftest.py      # Fixtures
├── pyproject.toml
├── README.md
└── claude.md
```

## Operations Supported

### 1. Add Comment
```python
input_data = AddCommentInput(
    issue_key="PROJ-123",
    comment="This is a comment"
)
response = await client.add_comment(input_data)
```

### 2. Get Issue
```python
input_data = GetIssueInput(issue_key="PROJ-123")
response = await client.get_issue(input_data)
```

### 3. Create Issue
```python
input_data = CreateIssueInput(
    project_key="PROJ",
    summary="Bug title",
    description="Bug description",
    issue_type="Bug"
)
response = await client.create_issue(input_data)
```

### 4. Transition Issue
```python
input_data = TransitionIssueInput(
    issue_key="PROJ-123",
    transition_id="31"
)
response = await client.transition_issue(input_data)
```

## Type Safety Examples

### Strict Models
```python
from pydantic import BaseModel, Field, ConfigDict

class AddCommentInput(BaseModel):
    model_config = ConfigDict(strict=True)  # ✅ REQUIRED

    issue_key: str = Field(..., min_length=1)
    comment: str = Field(..., min_length=1)
```

### NO Any Types
```python
# Bad ❌
def process(data: Any) -> dict:
    return data

# Good ✅
def process(data: AddCommentInput) -> AddCommentResponse:
    return AddCommentResponse(success=True, ...)
```

## Error Handling

### Custom Exceptions
```python
class JiraClientError(Exception):
    """Base exception."""

class JiraAuthenticationError(JiraClientError):
    """Auth failed (401)."""

class JiraNotFoundError(JiraClientError):
    """Resource not found (404)."""

class JiraValidationError(JiraClientError):
    """Invalid request (400)."""

class JiraRateLimitError(JiraClientError):
    """Rate limit exceeded (429)."""

class JiraServerError(JiraClientError):
    """Server error (5xx)."""
```

### Usage
```python
try:
    response = await client.add_comment(input_data)
except JiraAuthenticationError:
    logger.error("jira_auth_failed")
    raise
except JiraNotFoundError as e:
    logger.error("jira_issue_not_found", issue_key=input_data.issue_key)
    raise
```

## Authentication

### Basic Auth
```python
client = JiraClient(
    email="user@example.com",
    api_token="your-api-token",
    domain="your-domain.atlassian.net"
)
```

### Headers
```python
headers = {
    "Authorization": f"Basic {base64_encoded_credentials}",
    "Content-Type": "application/json"
}
```

## Testing

### Requirements
- ✅ Tests run fast (< 5s per file)
- ✅ Mock HTTP calls with respx
- ✅ NO real API calls
- ✅ 100% type coverage

### Example
```python
import pytest
import respx
import httpx

@pytest.mark.asyncio
@respx.mock
async def test_add_comment_success():
    respx.post("https://your-domain.atlassian.net/rest/api/3/issue/PROJ-123/comment").mock(
        return_value=httpx.Response(201, json={"id": "10001"})
    )

    client = JiraClient(email="test@example.com", api_token="token", domain="your-domain")
    input_data = AddCommentInput(issue_key="PROJ-123", comment="Test")

    response = await client.add_comment(input_data)

    assert response.success is True
    assert response.comment_id == "10001"
```

## Used By

### MCP Server (integrations/mcp-servers/jira)
```python
from jira_client import JiraClient, AddCommentInput

client = JiraClient(...)
result = await client.add_comment(AddCommentInput(...))
```

### REST API (integrations/api/jira)
```python
from jira_client import JiraClient, GetIssueInput

client = JiraClient(...)
result = await client.get_issue(GetIssueInput(...))
```

## Performance

### Connection Pooling
```python
async with httpx.AsyncClient() as client:
    # Reuses connections automatically
    response1 = await client.post(...)
    response2 = await client.post(...)
```

### Rate Limiting
- Jira rate limits: 10 requests/second per user
- Client handles 429 responses
- Exponential backoff on rate limit errors

## Development

### Install
```bash
cd integrations/packages/jira_client
uv sync
```

### Run Tests
```bash
uv run pytest tests/ -v
```

### Build
```bash
uv build
```

## API Reference

### JiraClient Methods

#### add_comment
```python
async def add_comment(self, input_data: AddCommentInput) -> AddCommentResponse:
    """Add comment to Jira issue."""
```

#### get_issue
```python
async def get_issue(self, input_data: GetIssueInput) -> JiraIssueResponse:
    """Get Jira issue details."""
```

#### create_issue
```python
async def create_issue(self, input_data: CreateIssueInput) -> CreateIssueResponse:
    """Create new Jira issue."""
```

#### transition_issue
```python
async def transition_issue(self, input_data: TransitionIssueInput) -> TransitionIssueResponse:
    """Transition issue to new status."""
```

## Common Patterns

### Retry Logic
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def add_comment_with_retry(client, input_data):
    return await client.add_comment(input_data)
```

### Logging
```python
import structlog

logger = structlog.get_logger()

logger.info("jira_comment_added", issue_key=issue_key, comment_id=comment_id)
logger.error("jira_api_error", error=str(e), issue_key=issue_key)
```

## Summary

- 🔧 Shared Jira API client
- 🛡️ Strict type safety (NO `any`)
- ✅ < 300 lines per file
- 🔄 DRY - used by MCP and REST
- ⚡ Fast tests with respx
- 📝 Comprehensive error handling
- 🔐 Basic Auth with API token
