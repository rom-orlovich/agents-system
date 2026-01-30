# Slack Client - Shared API Client

Shared Slack API client for MCP servers and REST APIs. Single source of truth for all Slack operations.

## Installation

```bash
cd packages/slack_client
uv sync
```

## Usage

```python
from slack_client import (
    SlackClient,
    PostMessageInput,
    UpdateMessageInput,
    AddReactionInput,
)

client = SlackClient(bot_token="xoxb-your-bot-token")

input_data = PostMessageInput(
    channel="C12345",
    text="Hello from shared client!"
)

response = await client.post_message(input_data)
print(response.message)
```

## Features

- Strict type safety with Pydantic (NO `any` types)
- Comprehensive error handling
- Authentication via Bot Token
- Structured logging with structlog
- Thread support for replies

## Operations

### Post Message
```python
input_data = PostMessageInput(
    channel="C12345",
    text="Message text",
    thread_ts="1234567890.123456"  # Optional: reply in thread
)
response = await client.post_message(input_data)
```

### Update Message
```python
input_data = UpdateMessageInput(
    channel="C12345",
    ts="1234567890.123456",
    text="Updated message text"
)
response = await client.update_message(input_data)
```

### Add Reaction
```python
input_data = AddReactionInput(
    channel="C12345",
    timestamp="1234567890.123456",
    name="thumbsup"  # Without colons
)
response = await client.add_reaction(input_data)
```

## Error Handling

Custom exceptions for different error scenarios:

- `SlackAuthenticationError` - Invalid token or auth errors
- `SlackNotFoundError` - Channel or message not found
- `SlackValidationError` - Invalid request data
- `SlackRateLimitError` - Rate limit exceeded
- `SlackServerError` - Server errors (5xx)
- `SlackClientError` - Base exception for all errors

## Testing

```bash
cd packages/slack_client
uv run pytest tests/ -v
```

## Used By

- `packages/slack_mcp_server` - MCP server for agents
- `packages/slack_rest_api` - REST API for services
