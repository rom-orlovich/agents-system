# Agent Engine

Scalable task execution engine (port 8080-8089). Consumes tasks from Redis queue, executes via CLI providers (Claude/Cursor), and posts results back.

## CLI Provider Selection

Set via `CLI_PROVIDER` environment variable:

- `claude`: `claude -p --output-format stream-json`
- `cursor`: `agent chat --print --output-format json-stream`

## Agent Routing

**IMPORTANT**: Brain routes tasks based on source and task type:

**Source-Based**: GitHub Issue → `github-issue-handler`, GitHub PR → `github-pr-review`, Jira → `jira-code-plan`, Slack → `slack-inquiry`, Sentry → `sentry-error-handler`

**Task Type**: Discovery → `planning`, Implementation → `executor`, Verification → `verifier`, Integration → `service-integrator`

## Response Posting

**MUST**: After completing a task, agents MUST post responses back to source:

- GitHub: `github:add_issue_comment` (works for issues and PRs)
- Jira: `jira:add_jira_comment`
- Slack: `slack:post_message` (with `thread_ts` to reply in thread)
- Sentry: `sentry:add_sentry_comment` (if available)

## Folder Structure

```
agent-engine/
├── main.py              # FastAPI app + task worker
├── cli/                 # CLI providers (claude.py, cursor.py)
├── config/              # Settings
├── .claude/             # Agents and skills
│   ├── agents/          # 13 agent definitions
│   └── skills/          # 9 skill definitions
└── tests/               # Co-located tests
    ├── factories/       # Task and session factories
    ├── conftest.py      # Shared fixtures
    └── test_*.py        # Test files
```

## Testing

Tests are co-located with the service for portability.

```bash
# From agent-bot root
make test-agent-engine

# Or directly
cd agent-bot
PYTHONPATH=agent-engine:$PYTHONPATH uv run pytest agent-engine/tests/ -v
```

### Test Factories

Import factories from `tests/factories/`:

```python
from .factories import TaskFactory, SessionFactory, TaskStatus
from .factories.task_factory import InvalidTransitionError, VALID_TRANSITIONS
```

## Environment Variables

- `CLI_PROVIDER`: `claude` or `cursor`
- `MAX_CONCURRENT_TASKS`: Maximum parallel tasks (default: 5)
- `TASK_TIMEOUT_SECONDS`: Task timeout limit (default: 3600)
- `REDIS_URL`: Redis connection string
- `DATABASE_URL`: PostgreSQL connection string
- `KNOWLEDGE_GRAPH_URL`: Knowledge graph service URL

## Development Rules

- Maximum 300 lines per file
- NO `any` types - use strict Pydantic models
- NO comments - self-explanatory code only
- Tests must run fast (< 5 seconds), no real network calls
- Use async/await for all I/O operations
