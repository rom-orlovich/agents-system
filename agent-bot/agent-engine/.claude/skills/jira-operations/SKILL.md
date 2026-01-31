---
name: jira-operations
description: Jira API operations for issues, comments, transitions, and workflow management. Use when working with Jira tickets, posting comments, updating issues, or managing Jira workflows.
---

Jira operations using MCP tools for all API interactions.

## Quick Reference

- **Workflow**: See [flow.md](flow.md) for complete workflow guide and templates

## Key Principles

1. **Always use MCP tools** (`jira:*`) for API operations
2. **Use markdown** - MCP automatically converts to ADF
3. **Post responses** using MCP tools after task completion

## Environment

- `JIRA_API_TOKEN` - Jira API token
- `JIRA_BASE_URL` - Jira instance URL (e.g., https://yourcompany.atlassian.net)
- `JIRA_USER_EMAIL` - User email for authentication

## MCP Operations

**Always use MCP tools for Jira API operations:**

- `jira:add_jira_comment` - Add comments (markdown auto-converted to ADF)
- `jira:get_issue` - Get issue details
- `jira:update_issue` - Update issue fields
- `jira:transition_issue` - Change issue status
- `jira:search_issues` - Search with JQL

**MCP tools are documented in [flow.md](flow.md)** including:

- Comment posting with markdown
- Issue updates and transitions
- JQL search examples

## Response Posting

**IMPORTANT**: Always post responses after task completion using `jira:add_jira_comment`.

MCP automatically converts markdown to ADF format - no manual conversion needed.

See [flow.md](flow.md) for workflow examples and [templates.md](templates.md) for response templates.
