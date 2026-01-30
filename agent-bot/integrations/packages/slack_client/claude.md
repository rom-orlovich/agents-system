# Slack Client Package

## Purpose
Shared Python client library for Slack API integration, providing type-safe methods for messaging and channel operations.

## Architecture

### Component Type
**Shared Package** - Base layer dependency for Slack integrations

### Dependencies
- `httpx`: Async HTTP client
- `pydantic`: Data validation with strict types
- `structlog`: Structured logging

### Dependents
- `integrations/api/slack/slack_rest_api/`: REST API wrapper
- `integrations/mcp-servers/slack/slack_mcp_server/`: MCP protocol server

## Key Files

### Core Implementation
- `slack_client/client.py` (207 lines): Main SlackClient class
- `slack_client/models.py` (49 lines): Pydantic models for requests/responses
- `slack_client/exceptions.py` (22 lines): Custom exceptions
- `slack_client/__init__.py` (33 lines): Public API exports

### Tests
- `tests/test_client.py` (254 lines): Comprehensive client tests

## Pydantic Models

### Request Models
```python
class PostMessageInput(BaseModel):
    model_config = ConfigDict(strict=True)
    channel: str
    text: str
    thread_ts: str | None = None

class UpdateMessageInput(BaseModel):
    model_config = ConfigDict(strict=True)
    channel: str
    ts: str
    text: str

class AddReactionInput(BaseModel):
    model_config = ConfigDict(strict=True)
    channel: str
    timestamp: str
    name: str  # e.g., "rocket", "eyes"
```

### Response Models
```python
class PostMessageResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    ok: bool
    channel: str
    ts: str
    message: dict[str, str | bool]

class SlackMessage(BaseModel):
    model_config = ConfigDict(strict=True)
    type: str
    user: str
    text: str
    ts: str
```

## SlackClient API

### Initialization
```python
from slack_client import SlackClient

client = SlackClient(
    bot_token="xoxb-xxxxxxxxxxxxx",
    base_url="https://slack.com/api/"
)
```

### Methods

#### Post Message
```python
result = await client.post_message(
    PostMessageInput(
        channel="C1234567890",
        text="Agent completed code review ✅",
        thread_ts="1234567890.123456"  # Optional: Reply in thread
    )
)
```

#### Update Message
```python
result = await client.update_message(
    UpdateMessageInput(
        channel="C1234567890",
        ts="1234567890.123456",
        text="Updated: Code review complete with 3 issues found"
    )
)
```

#### Add Reaction
```python
result = await client.add_reaction(
    AddReactionInput(
        channel="C1234567890",
        timestamp="1234567890.123456",
        name="rocket"
    )
)
```

#### Get Channel History
```python
messages = await client.get_channel_history(
    channel="C1234567890",
    limit=10
)
```

## Error Handling

### Custom Exceptions
```python
class SlackClientError(Exception): ...
class SlackAuthenticationError(SlackClientError): ...
class SlackChannelNotFoundError(SlackClientError): ...
class SlackRateLimitError(SlackClientError): ...
```

### Slack API Errors
```python
{
    "ok": false,
    "error": "invalid_auth"  → SlackAuthenticationError
    "error": "channel_not_found"  → SlackChannelNotFoundError
    "error": "rate_limited"  → SlackRateLimitError
}
```

## Usage Examples

### Complete Workflow
```python
from slack_client import SlackClient, PostMessageInput, AddReactionInput

client = SlackClient(bot_token=token)

try:
    response = await client.post_message(
        PostMessageInput(
            channel="C1234567890",
            text="Starting code review for PR #123"
        )
    )

    await client.add_reaction(
        AddReactionInput(
            channel=response.channel,
            timestamp=response.ts,
            name="eyes"
        )
    )

    await client.update_message(
        UpdateMessageInput(
            channel=response.channel,
            ts=response.ts,
            text="Code review complete ✅ Found 0 issues"
        )
    )

    await client.add_reaction(
        AddReactionInput(
            channel=response.channel,
            timestamp=response.ts,
            name="rocket"
        )
    )
except SlackAuthenticationError:
    logger.error("invalid_slack_token")
except SlackChannelNotFoundError:
    logger.error("slack_channel_not_found")
```

## Development

### Install Dependencies
```bash
cd integrations/packages/slack_client
pip install -e .
```

### Run Tests
```bash
pytest tests/ -v
pytest tests/ --cov=slack_client
```

### Type Checking
```bash
mypy slack_client/
```

## Configuration

### Environment Variables
```bash
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxx
SLACK_BASE_URL=https://slack.com/api/  # Optional
```

### Authentication
Requires Slack Bot Token with scopes:
- `chat:write`: Post messages
- `chat:write.public`: Post to any channel
- `reactions:write`: Add reactions
- `channels:history`: Read messages

## Integration Points

### Webhook Flow
1. Slack → Slash Command/Event → API Gateway
2. API Gateway → Task Queue
3. Agent Container → Slack Client → Slack API
4. Result → Slack (message/reaction)

### MCP Server
```python
# integrations/mcp-servers/slack/
from slack_client import SlackClient

@mcp.tool
async def slack_post_message(channel: str, text: str):
    client = SlackClient(...)
    return await client.post_message(
        PostMessageInput(channel=channel, text=text)
    )
```

## Best Practices

### Type Safety
- All models use `ConfigDict(strict=True)`
- No `Any` types
- Explicit field validation

### Error Handling
- Always wrap client calls in try/except
- Log errors with structlog
- Handle rate limits with retry

### Threading
- Use `thread_ts` for conversations
- Keep related messages in threads
- Main channel for notifications only

### Formatting
- Use Slack markdown (not GitHub markdown)
- Format code with backticks
- Use emoji reactions for status

## Rate Limiting
- Tier 1: 1 request/second
- Tier 2: 20 requests/minute
- Tier 3: 50 requests/minute
- Client implements exponential backoff

## Slack Markdown

### Formatting
```
*bold*
_italic_
~strikethrough~
`code`
```code block```
```

### Links
```
<https://example.com|Link Text>
<#C1234|channel>
<@U1234|user>
```

### Lists
```
• Bullet point (using Unicode)
1. Numbered list
2. Another item
```

## Security
- Never log bot tokens
- Use environment variables for credentials
- Validate all inputs with Pydantic
- Sanitize user input before posting
- Respect channel permissions
