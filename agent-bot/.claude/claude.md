# Agent Bot - Claude Code Configuration

## Project Overview

Production-ready webhook-driven AI agent system with:

- ⚡ Immediate webhook responses (< 100ms)
- 📊 Streaming logs (like Claude Code)
- 🎯 Direct result posting to external services
- 🔄 DRY principle with monorepo structure
- 🛡️ Strict type safety (NO `any` types)

## Critical Rules

### MUST READ FIRST

📖 **[.claude/rules/project-best-practices.md](./.claude/rules/project-best-practices.md)**

### Key Requirements

- ❌ **NO file > 300 lines** - Split into modules (constants, utils, models, etc.)
- ❌ **NO `any` types** - Always explicit types with Pydantic `strict=True`
- ❌ **NO comments in code** - Self-explanatory code only
- ✅ **Tests MUST pass gracefully** - Fast (< 5s per file), no flaky tests
- ✅ **Structured logging ONLY** - `logger.info("event", key=value)`
- ✅ **Async/await for I/O** - NO blocking sync code

## Directory Structure

```
agent-bot/
├── integrations/                # Monorepo (DRY principle)
│   ├── packages/                # Shared API clients
│   │   ├── jira_client/         # Single source of truth
│   │   ├── slack_client/
│   │   └── sentry_client/
│   ├── mcp-servers/             # MCP servers (use packages)
│   │   ├── jira/
│   │   ├── slack/
│   │   └── sentry/
│   └── api/                     # REST APIs (use packages)
│       ├── jira/
│       ├── slack/
│       └── sentry/
├── api-gateway/                 # Webhook receiver (immediate response)
├── agent-container/             # Task processor (async, streaming)
└── dashboard-api-container/     # Log viewer, analytics
```

## Architecture Principles

### 1. Immediate Webhook Response

```
Webhook → API Gateway → Redis Queue → RETURN 200 OK ⚡
                            ↓
                      Agent processes ASYNC
```

### 2. Streaming Logs

```
stream.jsonl:
{"event_type":"progress","stage":"initialization","message":"Task received"}
{"event_type":"execution","message":"Starting CLI"}
{"event_type":"mcp_call","tool_name":"github_post_pr_comment"}
{"event_type":"completion","success":true}
```

### 3. Direct Result Posting

```
Agent → MCP Client → github_post_pr_comment(pr=42, comment="✅ Done!")
                 ↘ github_add_pr_reaction(pr=42, reaction="rocket")
```

## Development Workflow

### Before Writing Code

1. Read `.claude/rules/project-best-practices.md`
2. Check file size limits (300 lines max)
3. Plan module structure if needed

### During Development

1. Use explicit types (NO `any`)
2. Keep functions focused and small
3. Write self-explanatory code
4. Use structured logging
5. Split files before hitting 300 lines

### Before Committing

- [ ] All files < 300 lines
- [ ] NO `any` types
- [ ] NO comments in code
- [ ] All tests pass gracefully
- [ ] Tests run fast
- [ ] Structured logging used
- [ ] README updated if needed

## Testing Requirements

### Speed

- ✅ < 5 seconds per test file
- ✅ Use mocks for external dependencies
- ❌ NO real network calls
- ❌ NO time.sleep()

### Quality

- ✅ Tests MUST pass gracefully
- ✅ NO flaky tests
- ✅ 100% type coverage
- ✅ Use `pytest-asyncio` for async

### Example

```python
@pytest.mark.asyncio
async def test_success_case(mock_client):
    result = await service.execute()
    assert result.success is True
```

## Available Skills

Located in `.claude/skills/`:

- `mcp-integration.md` - Using MCP servers
- `skill-creator.md` - Creating new skills
- `agent-creator.md` - Creating sub-agents

## Documentation

Main documentation is in the `docs/` folder:

- **[docs/ARCHITECTURE_FINAL.md](../docs/ARCHITECTURE_FINAL.md)** - Complete architecture documentation
- **[docs/SETUP.md](../docs/SETUP.md)** - Setup guide with OAuth, database, CLI configuration
- **[docs/TESTING.md](../docs/TESTING.md)** - Testing guide and requirements

Component-specific documentation:

- `api-gateway/claude.md` - Webhook handling
- `agent-container/.claude/claude.md` - Task processing

## Quick Reference

### File Size Limit

```bash
# Check file sizes
wc -l **/*.py | awk '$1 > 300 {print $1, $2}'
```

### Run Tests

```bash
# All tests
pytest -v

# Fast tests only
pytest -v --durations=10
```

### Type Checking

```bash
mypy . --strict
```

## Common Patterns

### Splitting Large Files

```python
# Before (400 lines) ❌
# client.py
class Client:
    # 400 lines

# After ✅
# constants.py (50 lines)
BASE_URL = "..."

# models.py (100 lines)
class Request(BaseModel):
    ...

# exceptions.py (50 lines)
class ClientError(Exception):
    ...

# client.py (200 lines)
from .constants import BASE_URL
from .models import Request
from .exceptions import ClientError

class Client:
    # Core logic only
```

### Type Safety

```python
# Bad ❌
def process(data: Any) -> dict:
    return data

# Good ✅
def process(data: ProcessInput) -> ProcessOutput:
    return ProcessOutput(result=data.value)
```

### Structured Logging

```python
# Bad ❌
logger.info(f"Task {task_id} started")

# Good ✅
logger.info("task_started", task_id=task_id)
```

## Support

- Issues: GitHub Issues
- Documentation: See README files in each component
- Rules: `.claude/rules/project-best-practices.md`

## License

MIT
