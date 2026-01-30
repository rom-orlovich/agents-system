# Sentry Client - Shared API Client

Shared Sentry API client for MCP servers and REST APIs. Single source of truth for all Sentry operations.

## Installation

```bash
cd packages/sentry_client
uv sync
```

## Usage

```python
from sentry_client import (
    SentryClient,
    AddCommentInput,
    UpdateIssueStatusInput,
    GetIssueInput,
    AssignIssueInput,
    AddTagInput,
)

client = SentryClient(
    auth_token="your-auth-token",
    org_slug="your-org",
    project_slug="your-project"
)

input_data = AddCommentInput(
    issue_id="123456",
    comment="This is a test comment"
)

response = await client.add_comment(input_data)
print(response.message)
```

## Features

- Strict type safety with Pydantic (NO `any` types)
- Comprehensive error handling
- Authentication via Bearer token
- Structured logging with structlog
- Literal types for status values

## Operations

### Add Comment
```python
input_data = AddCommentInput(issue_id="123456", comment="Comment text")
response = await client.add_comment(input_data)
```

### Update Issue Status
```python
input_data = UpdateIssueStatusInput(
    issue_id="123456",
    status="resolved"  # Must be: "resolved", "unresolved", or "ignored"
)
response = await client.update_issue_status(input_data)
```

### Get Issue
```python
input_data = GetIssueInput(issue_id="123456")
response = await client.get_issue(input_data)
```

### Assign Issue
```python
input_data = AssignIssueInput(
    issue_id="123456",
    assignee="dev@example.com"
)
response = await client.assign_issue(input_data)
```

### Add Tag
```python
input_data = AddTagInput(
    issue_id="123456",
    key="environment",
    value="production"
)
response = await client.add_tag(input_data)
```

## Error Handling

Custom exceptions for different error scenarios:

- `SentryAuthenticationError` - Invalid auth token (401)
- `SentryNotFoundError` - Issue not found (404)
- `SentryValidationError` - Invalid request data (400)
- `SentryRateLimitError` - Rate limit exceeded (429)
- `SentryServerError` - Server errors (5xx)
- `SentryClientError` - Base exception for all errors

## Testing

```bash
cd packages/sentry_client
uv run pytest tests/ -v
```

## Used By

- `packages/sentry_mcp_server` - MCP server for agents
- `packages/sentry_rest_api` - REST API for services
