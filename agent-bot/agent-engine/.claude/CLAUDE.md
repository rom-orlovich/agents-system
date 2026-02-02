# Agent Engine

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

## Environment Variables

- `CLI_PROVIDER`: `claude` or `cursor`
- `MAX_CONCURRENT_TASKS`: Maximum parallel tasks (default: 5)
- `TASK_TIMEOUT_SECONDS`: Task timeout limit (default: 3600)
- `KNOWLEDGE_GRAPH_URL`: Knowledge graph service URL
