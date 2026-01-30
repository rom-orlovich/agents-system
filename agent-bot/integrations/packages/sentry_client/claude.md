# Sentry Client Package

## Purpose
Shared Python client library for Sentry API integration, providing type-safe methods for error tracking operations.

## Architecture

### Component Type
**Shared Package** - Base layer dependency for Sentry integrations

### Dependencies
- `httpx`: Async HTTP client
- `pydantic`: Data validation with strict types
- `structlog`: Structured logging

### Dependents
- `integrations/api/sentry/sentry_rest_api/`: REST API wrapper
- `integrations/mcp-servers/sentry/sentry_mcp_server/`: MCP protocol server

## Key Files

### Core Implementation
- `sentry_client/client.py` (246 lines): Main SentryClient class
- `sentry_client/models.py` (79 lines): Pydantic models for requests/responses
- `sentry_client/exceptions.py` (22 lines): Custom exceptions
- `sentry_client/__init__.py` (41 lines): Public API exports

### Tests
- `tests/test_client.py` (208 lines): Comprehensive client tests

## Pydantic Models

### Request Models
```python
class AddCommentInput(BaseModel):
    model_config = ConfigDict(strict=True)
    issue_id: str
    comment: str

class UpdateIssueStatusInput(BaseModel):
    model_config = ConfigDict(strict=True)
    issue_id: str
    status: Literal["resolved", "ignored", "unresolved"]

class GetIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)
    issue_id: str
```

### Response Models
```python
class SentryIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    id: str
    title: str
    status: str
    level: str
    project: str
    count: int
    first_seen: str
    last_seen: str

class AddCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    id: str
    comment: str
    created_at: str
```

## SentryClient API

### Initialization
```python
from sentry_client import SentryClient

client = SentryClient(
    auth_token="sntrys_xxxxxxxxxxxxxxxxxxxxx",
    organization_slug="my-org",
    base_url="https://sentry.io/api/0/"
)
```

### Methods

#### Add Comment
```python
result = await client.add_comment(
    AddCommentInput(
        issue_id="1234567890",
        comment="Investigation started by agent"
    )
)
```

#### Update Issue Status
```python
result = await client.update_issue_status(
    UpdateIssueStatusInput(
        issue_id="1234567890",
        status="resolved"
    )
)
```

#### Get Issue Details
```python
issue = await client.get_issue(
    GetIssueInput(issue_id="1234567890")
)
```

## Error Handling

### Custom Exceptions
```python
class SentryClientError(Exception): ...
class SentryAuthenticationError(SentryClientError): ...
class SentryNotFoundError(SentryClientError): ...
class SentryRateLimitError(SentryClientError): ...
```

### HTTP Status Mapping
- `401`: SentryAuthenticationError
- `404`: SentryNotFoundError
- `429`: SentryRateLimitError
- Other 4xx/5xx: SentryClientError

## Usage Examples

### Complete Workflow
```python
from sentry_client import SentryClient, AddCommentInput

client = SentryClient(auth_token=token, organization_slug="acme")

try:
    issue = await client.get_issue(
        GetIssueInput(issue_id="123")
    )

    await client.add_comment(
        AddCommentInput(
            issue_id="123",
            comment=f"Analyzing error: {issue.title}"
        )
    )

    await client.update_issue_status(
        UpdateIssueStatusInput(
            issue_id="123",
            status="resolved"
        )
    )
except SentryAuthenticationError:
    logger.error("invalid_sentry_token")
except SentryNotFoundError:
    logger.error("sentry_issue_not_found")
```

## Development

### Install Dependencies
```bash
cd integrations/packages/sentry_client
pip install -e .
```

### Run Tests
```bash
pytest tests/ -v
pytest tests/ --cov=sentry_client
```

### Type Checking
```bash
mypy sentry_client/
```

## Configuration

### Environment Variables
```bash
SENTRY_AUTH_TOKEN=sntrys_xxxxxxxxxxxxxxxxxxxxx
SENTRY_ORGANIZATION=my-org
SENTRY_BASE_URL=https://sentry.io/api/0/  # Optional
```

### Authentication
Requires Sentry API token with scopes:
- `event:read`
- `event:write`
- `project:read`
- `org:read`

## Integration Points

### Webhook Flow
1. Sentry → Webhook → API Gateway
2. API Gateway → Task Queue
3. Agent Container → Sentry Client → Sentry API
4. Result → Sentry (comment/status update)

### MCP Server
```python
# integrations/mcp-servers/sentry/
from sentry_client import SentryClient

@mcp.tool
async def sentry_add_comment(issue_id: str, comment: str):
    client = SentryClient(...)
    return await client.add_comment(
        AddCommentInput(issue_id=issue_id, comment=comment)
    )
```

## Best Practices

### Type Safety
- All models use `ConfigDict(strict=True)`
- No `Any` types
- Explicit Literal types for enums

### Error Handling
- Always wrap client calls in try/except
- Log errors with structlog
- Propagate exceptions appropriately

### Testing
- Mock httpx responses
- Test all error conditions
- Verify request formatting
- Check response parsing

## Rate Limiting
- Sentry API: 100 requests/minute
- Client implements exponential backoff
- Retry on 429 status (rate limit)

## Security
- Never log auth tokens
- Use environment variables for credentials
- Validate all inputs with Pydantic
- Sanitize comments before posting
