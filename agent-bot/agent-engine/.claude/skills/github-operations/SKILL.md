---
name: github-operations
description: GitHub API operations and repository workflow for issues, PRs, commits, and branch management. Use when working with GitHub repositories, creating issues/PRs, posting comments, or managing repository workflows.
---

GitHub operations using MCP tools for API interactions and local git commands for repository management.

> **IMPORTANT:** Always use MCP tools (`github:*`) for API operations. Use local git commands for repository management only.

## Quick Reference

- **Workflow**: See [flow.md](flow.md) for complete workflow guide and templates

## Key Principles

1. **Always use MCP tools** (`github:*`) for API operations
2. **Use local git commands** for repository management
3. **Post responses** using MCP tools after task completion

## Environment

- `GITHUB_TOKEN` - GitHub personal access token (required for MCP authentication)

## MCP Operations

**Always use MCP tools for GitHub API operations:**

- `github:get_file_content` - Get file contents
- `github:search_code` - Search code across repositories
- `github:create_pull_request` - Create PRs
- `github:add_issue_comment` - Post comments on issues/PRs
- `github:get_pull_request` - Get PR details
- `github:create_or_update_file` - Commit file changes

**MCP tools are documented in [flow.md](flow.md) with examples.**

## Repository Workflow

Repositories are pre-cloned by Docker at startup (via `GITHUB_REPOS` env var). If repository doesn't exist, clone it first.

**Workflow:** Check repository → Update (`git pull`) → Create feature branch → Make changes → Commit → Push → Create PR

**Branch naming:** `fix/issue-123`, `feature/add-auth`, `refactor/cleanup-module`

See [flow.md](flow.md) for complete workflow details.

### Response Posting

**IMPORTANT**: Always post responses after task completion using `github:add_issue_comment`.

See [flow.md](flow.md) for workflow examples and [templates.md](templates.md) for response templates.

## Workflows

See [flow.md](flow.md) for complete workflow examples including:

- Complexity-based approach selection (MCP tools vs cloned repository)
- Repository management
- Creating pull requests
- Posting responses
