# Agent Engine CLAUDE.md

## Overview

This is the brain of the agent system. The Agent Engine processes tasks from the Redis queue, executes them using the configured CLI provider (Claude or Cursor), and reports results back.

## Agent Routing

The brain agent routes incoming tasks to specialized agents based on the source and content:

### Source-Based Routing

| Source | Agent | Description |
|--------|-------|-------------|
| GitHub Issue | `github-issue-handler` | Handles new issues and issue comments |
| GitHub PR | `github-pr-review` | Handles PR reviews and comments |
| Jira Ticket | `jira-code-plan` | Handles Jira tickets with AI-Fix label |
| Slack Message | `slack-inquiry` | Handles questions in Slack channels |
| Sentry Alert | `sentry-error-handler` | Handles Sentry error alerts |

### Task Type Routing

| Task Type | Agent | Description |
|-----------|-------|-------------|
| Discovery | `planning` | Code discovery and analysis |
| Implementation | `executor` | TDD-based code implementation |
| Verification | `verifier` | Code quality verification |
| Integration | `service-integrator` | External service coordination |

## Available MCP Tools

The agent has access to tools from:

- **github**: Repository, issue, PR, and file operations
- **jira**: Issue creation, updates, comments, transitions
- **slack**: Message sending, channel history, reactions
- **sentry**: Error tracking, issue resolution

## Response Posting

After completing a task, agents should post responses back to the source:

1. **GitHub**: Use `create_issue_comment` or `create_pr_review_comment`
2. **Jira**: Use `add_jira_comment`
3. **Slack**: Use `send_slack_message` (reply in thread)
4. **Sentry**: Use `add_sentry_comment`

## Task Lifecycle

1. Task arrives in Redis queue
2. Worker picks up task
3. Brain routes to appropriate agent
4. Agent executes using CLI provider
5. Response posted to source
6. Task marked complete

## Environment Variables

- `CLI_PROVIDER`: claude or cursor
- `MAX_CONCURRENT_TASKS`: Maximum parallel tasks
- `TASK_TIMEOUT_SECONDS`: Task timeout limit
