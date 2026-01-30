# Jira Client - Shared API Client

Shared Jira API client for MCP servers and REST APIs. Single source of truth for all Jira operations.

## Installation

```bash
cd packages/jira_client
uv sync
```

## Usage

```python
from jira_client import (
    JiraClient,
    AddCommentInput,
    GetIssueInput,
    CreateIssueInput,
    TransitionIssueInput,
)

client = JiraClient(
    email="your-email@example.com",
    api_token="your-api-token",
    domain="your-domain.atlassian.net"
)

input_data = AddCommentInput(
    issue_key="PROJ-123",
    comment="This is a test comment"
)

response = await client.add_comment(input_data)
print(response.message)
```

## Features

- Strict type safety with Pydantic (NO `any` types)
- Comprehensive error handling
- Authentication via Basic Auth (email + API token)
- Structured logging with structlog

## Operations

### Add Comment
```python
input_data = AddCommentInput(issue_key="PROJ-123", comment="Comment text")
response = await client.add_comment(input_data)
```

### Get Issue
```python
input_data = GetIssueInput(issue_key="PROJ-123")
response = await client.get_issue(input_data)
```

### Create Issue
```python
input_data = CreateIssueInput(
    project_key="PROJ",
    summary="Issue title",
    description="Issue description",
    issue_type="Task"
)
response = await client.create_issue(input_data)
```

### Transition Issue
```python
input_data = TransitionIssueInput(
    issue_key="PROJ-123",
    transition_id="31"
)
response = await client.transition_issue(input_data)
```

## Error Handling

Custom exceptions for different error scenarios:

- `JiraAuthenticationError` - Invalid credentials (401)
- `JiraNotFoundError` - Resource not found (404)
- `JiraValidationError` - Invalid request data (400)
- `JiraRateLimitError` - Rate limit exceeded (429)
- `JiraServerError` - Server errors (5xx)
- `JiraClientError` - Base exception for all errors

## Testing

```bash
cd packages/jira_client
uv run pytest tests/ -v
```

## Used By

- `packages/jira_mcp_server` - MCP server for agents
- `packages/jira_rest_api` - REST API for services
