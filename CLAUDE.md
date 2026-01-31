# Monorepo Conventions

## System Selection

**Recommended**: `claude-code-cli/` for production (75% success rate). See @README.md for system comparison.

## Key Commands

### Agent Bot (Most Active)

```bash
cd agent-bot
make init                    # Initialize project
make cli-up PROVIDER=claude SCALE=1  # Start Claude CLI
make cli-up PROVIDER=cursor SCALE=1  # Start Cursor CLI
make test                    # Run all tests
make db-migrate MSG="..."    # Create migration
```

### Other Systems

```bash
# Single Agent System
cd single-agent-system && python cli.py run --description "..."

# Multiple Agents System
cd multiple-agents-system && python cli.py run --ticket PROJ-123

# Claude Code CLI
cd claude-code-cli && ./scripts/setup-local.sh
```

## Critical Development Rules (Agent Bot)

**STRICT ENFORCEMENT**:

- **Maximum 300 lines per Python file** - Split into `constants.py`, `models.py`, `exceptions.py`, `core.py`
- **NO `any` types EVER** - Use `ConfigDict(strict=True)` in Pydantic models
- **NO comments in code** - Self-explanatory code only
- **Tests MUST run fast** (< 5 seconds per file), NO real network calls
- **ALWAYS use async/await** for I/O - Use `httpx.AsyncClient`, NOT `requests`
- **Structured logging**: `logger.info("task_started", task_id=task_id, user_id=user_id)`

## Testing

```bash
# Agent Bot
make test-unit              # Unit tests only
make test-integration       # Integration tests
make test-cli               # Test CLI in container

# Other systems
pytest tests/unit/          # Unit tests only
pytest -m integration      # Integration tests
```

## Code Quality

```bash
# Agent Bot
make format                 # Auto-format code
make lint                   # Run linting
mypy .                      # Type checking

# Check file sizes (300 line limit)
find . -name "*.py" -exec wc -l {} \; | awk '$1 > 300'
```

## TDD Workflow

1. **Red**: Write failing test
2. **Green**: Implement minimal code to pass
3. **Refactor**: Clean up while keeping tests green
4. **Verification**: Run tests (unit → integration → E2E)

## Git Workflow

**Commit format**:

```
<type>: <subject>

<detailed description>

https://claude.ai/code/session_<session_id>
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

**Branches**: `main`, `feature/*`, `fix/*`, `refactor/*`

## Environment Variables

Required for Agent Bot:

- `CLI_PROVIDER`: `claude` or `cursor`
- `POSTGRES_URL`, `REDIS_URL`
- API keys: `GITHUB_TOKEN`, `JIRA_API_TOKEN`, `SLACK_BOT_TOKEN`, `SENTRY_DSN`
- Webhook secrets: `GITHUB_WEBHOOK_SECRET`, `JIRA_WEBHOOK_SECRET`, `SLACK_WEBHOOK_SECRET`

See `agent-bot/.env.example` for complete list.

## When to Use Skills vs CLAUDE.md

- **CLAUDE.md**: Persistent conventions, workflows, commands Claude can't guess
- **Skills** (`.claude/skills/`): Domain knowledge or workflows only relevant sometimes
