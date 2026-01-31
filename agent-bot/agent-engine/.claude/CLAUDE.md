# Agent Engine CLAUDE.md

## Overview

This is the brain of the agent system. The Agent Engine processes tasks from the Redis queue, executes them using the configured CLI provider (Claude or Cursor), and reports results back.

## CLI Provider Selection

The agent engine supports two CLI providers:

| Provider | Command | Use Case |
|----------|---------|----------|
| `claude` | `claude -p --output-format stream-json` | Claude Code CLI for Anthropic API |
| `cursor` | `agent chat --print --output-format json-stream` | Cursor AI headless mode |

Set via `CLI_PROVIDER` environment variable.

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

## Available Skills

Skills are defined in `.claude/skills/` as markdown files:

| Skill | Description |
|-------|-------------|
| `discovery` | File search, code search, project structure |
| `knowledge-graph` | Semantic code search, dependency graphs, call analysis |

### Knowledge Graph Integration

The knowledge graph skill provides advanced code discovery:

- **Semantic search**: Find code by meaning, not just text
- **Dependency tracking**: See what imports/calls what
- **Call graph**: Trace function call chains
- **Symbol references**: Find all usages of a function/class

Access via MCP server on port 9005.

## Available MCP Tools

The agent has access to tools from:

- **github**: Repository, issue, PR, and file operations
- **jira**: Issue creation, updates, comments, transitions
- **slack**: Message sending, channel history, reactions
- **sentry**: Error tracking, issue resolution
- **knowledge-graph**: Semantic code search and navigation

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
4. Agent executes using CLI provider (Claude or Cursor)
5. Response posted to source
6. Task marked complete

## Environment Variables

- `CLI_PROVIDER`: `claude` or `cursor`
- `MAX_CONCURRENT_TASKS`: Maximum parallel tasks (default: 5)
- `TASK_TIMEOUT_SECONDS`: Task timeout limit (default: 3600)
- `KNOWLEDGE_GRAPH_URL`: Knowledge graph service URL
