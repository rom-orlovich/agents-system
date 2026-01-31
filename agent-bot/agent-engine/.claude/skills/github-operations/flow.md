# GitHub Operations Workflow

Complete workflow for handling GitHub operations using MCP tools.

## Workflow Overview

```
Task Received → Analyze Complexity → Choose Approach → Execute → Post Response
```

## Step-by-Step Workflow

### 1. Analyze Task Complexity

**Decision Logic:**

- **Use MCP tools** (`github:get_file_content`) if task contains: `search`, `find`, `check`, `view`, `get`, `show`, `list`, `read`
- **Use cloned repository** if task contains: `analyze`, `refactor`, `implement`, `fix`, `change`, `modify`, `update`, `multi`, `comprehensive`, `deep`, `complex`

**Example:**

- "search for config file" → Use MCP tools
- "refactor authentication module" → Use cloned repository

### 2. Choose Approach

#### MCP Tools (Simple Tasks)

1. Use `github:get_file_content` to fetch files
2. Use `github:search_code` to search across repositories
3. Analyze results
4. Post response using `github:add_issue_comment`

**Example:**

```
github:get_file_content → Analyze → github:add_issue_comment
```

#### Cloned Repository (Complex Tasks)

**Repositories are pre-cloned by Docker at startup.** If repository doesn't exist, clone it first:

```bash
# Check if repo exists
if [ ! -d "/app/repos/repo-name" ]; then
    git clone https://github.com/owner/repo-name.git /app/repos/repo-name
fi
```

Then proceed with workflow:

1. Navigate to cloned repository: `cd /app/repos/repo-name`
2. Update repository: `git pull origin main`
3. Create feature branch: `git checkout -b fix/issue-123`
4. Make changes
5. Commit changes: `git commit -m "fix: Description"`
6. Push branch: `git push origin fix/issue-123`
7. Create PR using `github:create_pull_request`
8. Post response using `github:add_issue_comment`

**Example:**

```
cd /app/repos/repo-name → git pull → git checkout -b branch → Make changes → git commit → git push → github:create_pull_request → github:add_issue_comment
```

### 3. Repository Management

**Pre-cloned Repositories:**

- Repositories are pre-cloned by Docker at startup (configure via `GITHUB_REPOS` env var)
- Located at `/app/repos/repo-name`
- If repository doesn't exist, clone it first
- Always pull latest before starting work

**Branch Naming:**

- Bug fixes: `fix/issue-123` or `fix/login-error`
- Features: `feature/add-authentication` or `feature/issue-456`
- Refactoring: `refactor/cleanup-auth-module`

**Commit Format:**

```
fix: Brief description

- Detailed change 1
- Detailed change 2

Fixes #123
```

### 4. Creating Pull Requests

**Use MCP tool:**

```
github:create_pull_request
```

**Required Parameters:**

- `owner`: Repository owner
- `repo`: Repository name
- `title`: PR title (e.g., "Fix: Issue #123 - Description")
- `head`: Source branch
- `base`: Target branch (usually "main")
- `body`: PR description (markdown)
- `draft`: Boolean (set `true` for draft PRs)

**See [templates.md](templates.md) for PR body templates.**

### 5. Posting Responses

**After task completion, always post response:**

**Use MCP tool:**

```
github:add_issue_comment
```

**See [templates.md](templates.md) for complete templates** including:

- Issue comment templates
- PR comment templates
- Error response templates
- MCP tool call examples

## Common Workflows

### Workflow 1: Issue Analysis

1. Receive GitHub issue
2. Use `github:get_file_content` to fetch relevant files
3. Analyze code
4. Post analysis using `github:add_issue_comment`

### Workflow 2: Bug Fix

1. Receive GitHub issue
2. Check if repository exists at `/app/repos/repo-name`, clone if needed
3. Navigate to repository: `cd /app/repos/repo-name`
4. Update repository: `git pull origin main`
5. Create branch: `git checkout -b fix/issue-123`
6. Make fixes
7. Commit: `git commit -m "fix: Description\n\nFixes #123"`
8. Push: `git push origin fix/issue-123`
9. Create PR: `github:create_pull_request`
10. Post comment: `github:add_issue_comment`

### Workflow 3: Code Review

1. Receive PR review request
2. Get PR details: `github:get_pull_request`
3. Review changed files:
   - Use `github:get_file_content` for each changed file
   - Skip large files (>1000 line changes)
   - Skip dependency lock files, minified files, binary files
   - Focus on code files (`.py`, `.ts`, `.js`, etc.)
4. Analyze changes:
   - Check for bugs, security issues
   - Verify code quality and best practices
   - Check test coverage
5. Post review comments: `github:add_issue_comment`

**Review Checklist:**

- [ ] Code follows project conventions
- [ ] No obvious bugs or security issues
- [ ] Tests included/updated
- [ ] Documentation updated if needed
- [ ] Performance considerations addressed

## Error Handling

**If task fails:**

1. Post error response using `github:add_issue_comment`
2. See [templates.md](templates.md) for error templates
3. Include error details and troubleshooting steps

## Best Practices

1. **Always use MCP tools** for API operations
2. **Use local git commands** for repository management
3. **Post responses** after every task completion
4. **Link commits to issues** using "Fixes #123" format
5. **Create draft PRs** for complex changes requiring review
6. **Use descriptive branch names** following conventions
7. **Pull latest changes** before starting work
8. **Use templates** from [templates.md](templates.md) for consistent formatting
