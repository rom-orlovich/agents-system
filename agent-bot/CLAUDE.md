# Agent Bot Development Rules

## Critical Rules

**STRICT ENFORCEMENT** - Must be followed for all agent-bot code:

### File Size Limits

- **Maximum 300 lines per file** (enforced)
- Split into: `constants.py`, `models.py`, `exceptions.py`, `core.py`
- Check: `find . -name "*.py" -exec wc -l {} \; | awk '$1 > 300'`

### Type Safety

- **NO `any` types EVER**
- Always use `ConfigDict(strict=True)` in Pydantic models
- Explicit types for all function signatures
- Use `Literal` for enums

### Code Style

- **NO comments in code** - Self-explanatory code only
- Use descriptive variable/function names
- Extract complex logic into named functions
- Only docstrings for public APIs

### Testing Requirements

- Tests MUST pass gracefully
- Tests MUST run fast (< 5 seconds per file)
- NO flaky tests, NO real network calls
- Use `pytest-asyncio` for async code

### Async/Await

- ALWAYS use async/await for I/O operations
- Use `httpx.AsyncClient`, NOT `requests`
- Use `asyncio.gather()` for parallel operations

### Structured Logging

```python
logger.info("task_started", task_id=task_id, user_id=user_id)
```

## Key Commands

```bash
make init                    # Initialize project
make cli-up PROVIDER=claude SCALE=1  # Start Claude CLI
make cli-up PROVIDER=cursor SCALE=1  # Start Cursor CLI
make test                    # Run all tests
make db-migrate MSG="..."    # Create migration
make db-upgrade              # Apply migrations
```

## Architecture

Microservices architecture with:

- `api-gateway/` - Webhook reception (port 8000)
- `agent-engine/` - Task execution (ports 8080-8089, scalable)
- `mcp-servers/` - MCP protocol servers (ports 9001-9004)
- `api-services/` - REST API wrappers (ports 3001-3004)
- `dashboard-api-container/` - Analytics (port 5000)

Services communicate via API/Queue only (NO direct imports).

## Environment Variables

```bash
CLI_PROVIDER=claude                    # or 'cursor'
POSTGRES_URL=postgresql://agent:agent@postgres:5432/agent_system
REDIS_URL=redis://redis:6379/0
GITHUB_TOKEN=ghp_xxx
JIRA_API_TOKEN=xxx
SLACK_BOT_TOKEN=xoxb-xxx
SENTRY_DSN=https://xxx@sentry.io/xxx
GITHUB_WEBHOOK_SECRET=xxx
JIRA_WEBHOOK_SECRET=xxx
SLACK_WEBHOOK_SECRET=xxx
```

## Health Checks

```bash
curl http://localhost:8000/health      # API Gateway
curl http://localhost:8080/health      # Agent Engine
make cli-status PROVIDER=claude        # CLI status
```
