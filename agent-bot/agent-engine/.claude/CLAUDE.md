# Agent Engine

## CLI Provider Selection

Set via `CLI_PROVIDER` environment variable:

| Provider | Command                                          | Use Case           |
| -------- | ------------------------------------------------ | ------------------ |
| `claude` | `claude -p --output-format stream-json`          | Claude Code CLI    |
| `cursor` | `agent chat --print --output-format json-stream` | Cursor AI headless |

## Agent Routing

**IMPORTANT**: The brain agent routes tasks based on source and task type:

### Source-Based Routing

| Source        | Agent                  | Description                            |
| ------------- | ---------------------- | -------------------------------------- |
| GitHub Issue  | `github-issue-handler` | Handles new issues and issue comments  |
| GitHub PR     | `github-pr-review`     | Handles PR reviews and comments        |
| Jira Ticket   | `jira-code-plan`       | Handles Jira tickets with AI-Fix label |
| Slack Message | `slack-inquiry`        | Handles questions in Slack channels    |
| Sentry Alert  | `sentry-error-handler` | Handles Sentry error alerts            |

### Task Type Routing

| Task Type      | Agent                | Description                   |
| -------------- | -------------------- | ----------------------------- |
| Discovery      | `planning`           | Code discovery and analysis   |
| Implementation | `executor`           | TDD-based code implementation |
| Verification   | `verifier`           | Code quality verification     |
| Integration    | `service-integrator` | External service coordination |

## Response Posting

**MUST**: After completing a task, agents MUST post responses back to source using MCP tools:

1. **GitHub**: Use `github:add_issue_comment` (works for both issues and PRs)
2. **Jira**: Use `jira:add_jira_comment`
3. **Slack**: Use `slack:post_message` (with `thread_ts` to reply in thread)
4. **Sentry**: Use `sentry:add_sentry_comment` (if available)

## Task Lifecycle

1. Task arrives in Redis queue
2. Worker picks up task
3. Brain routes to appropriate agent
4. Agent executes using CLI provider (Claude or Cursor)
5. Response posted to source
6. Task marked complete

## Environment Variables

- `CLI_PROVIDER`: `claude` or `cursor`
- `MAX_CONCURRENT_TASKS`: Maximum parallel tasks (default: 5)
- `TASK_TIMEOUT_SECONDS`: Task timeout limit (default: 3600)
- `KNOWLEDGE_GRAPH_URL`: Knowledge graph service URL
