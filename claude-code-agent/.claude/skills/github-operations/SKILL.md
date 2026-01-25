---
name: github-operations
description: GitHub API operations and repository workflow for issues, PRs, actions, releases, and branch management
user-invocable: false
---

GitHub operations using Python GitHub API client (HTTP-based), including repository workflow management.

> **IMPORTANT:** This skill uses the Python GitHub client (`core.github_client`) instead of `gh` CLI, as `gh` is not available in the Docker container. All operations use HTTP requests via `httpx`.

## Environment
- `GITHUB_TOKEN` - GitHub personal access token (required for API authentication)

## API Operations

### Issues
```python
from core.github_client import github_client
import asyncio

# Get issue details
issue = await github_client.get_issue("owner", "repo", 123)

# Post comment on issue
await github_client.post_issue_comment("owner", "repo", 123, "Fixed in PR #456")

# Update issue labels
await github_client.update_issue_labels("owner", "repo", 123, ["bug", "fixed"])
```

### Pull Requests
```python
from core.github_client import github_client
import asyncio

# Get PR details
pr = await github_client.get_pull_request("owner", "repo", 123)
print(f"PR #{pr['number']}: {pr['title']}")
print(f"State: {pr['state']}, Mergeable: {pr['mergeable']}")

# Get files changed in PR
files = await github_client.get_pr_files("owner", "repo", 123)
for file in files:
    print(f"  {file['filename']}: +{file['additions']} -{file['deletions']}")

# Post review comment
await github_client.post_pr_comment("owner", "repo", 123, "LGTM! ✅")

# Create new PR
pr_data = await github_client.create_pull_request(
    "owner", "repo",
    title="Fix: Authentication bug",
    head="fix/auth-bug",
    base="main",
    body="Fixes #123",
    draft=True
)
```

### Repository Operations
```python
from core.github_client import github_client
import asyncio

# Get repository information
repo_info = await github_client.get_repository_info("owner", "repo")
print(f"Name: {repo_info['name']}")
print(f"Description: {repo_info['description']}")
print(f"Stars: {repo_info['stargazers_count']}")

# Get repository languages
languages = await github_client.get_repository_languages("owner", "repo")
for lang, bytes_count in languages.items():
    print(f"{lang}: {bytes_count} bytes")

# Search code in repository
results = await github_client.search_code(
    "def authenticate",
    repo_owner="owner",
    repo_name="repo",
    max_results=10
)

# Get file content
content = await github_client.get_file_content(
    "owner", "repo",
    "path/to/file.py",
    ref="main"  # or branch name, tag, commit SHA
)
```

## Repository Workflow

Manages complete workflow for working with external GitHub repositories: cloning, persisting, updating, and branch management.

### Purpose

When working on issues from external GitHub repositories:
1. Clone repo on first use
2. Persist locally for future work
3. Pull latest changes before starting work
4. Always work in feature branches
5. Never push directly to main/master

### Workflow Steps

1. **Check if Repository Exists** - Verify if repo already cloned locally
2. **Clone Repository** - Clone if doesn't exist (first time only)
3. **Update Repository** - Pull latest changes from origin
4. **Create Feature Branch** - Create branch for issue/feature
5. **Work on Changes** - Make code changes, run tests
6. **Commit Changes** - Commit with proper message format
7. **Push and Create PR** - Push branch and create pull request

### Branch Naming Conventions

- Bug fixes: `fix/issue-123` or `fix/login-error`
- Features: `feature/add-authentication` or `feature/issue-456`
- Refactoring: `refactor/cleanup-auth-module`
- Documentation: `docs/update-readme`
- Tests: `test/add-integration-tests`

### Best Practices

- Always check if repo exists before cloning
- Always pull latest changes before starting work
- Always work in feature branches (never commit to main/master)
- Use descriptive branch names (`fix/issue-123`, `feature/add-auth`)
- Link commits to issues ("Fixes #123")
- Create PRs with context (include issue link and description)
- Clean up old branches after PR is merged

### Error Handling

- Repository not found: Verify access and repository name
- Authentication issues: Check `gh auth status`, re-authenticate if needed
- Merge conflicts: Resolve manually or reset branch

### Helper Scripts

Scripts available in `scripts/` directory:
- `setup_repo.sh` - Clone/update repo and create feature branch
- `commit_changes.sh` - Commit changes with proper format
- `create_pr.sh` - Create pull request after changes
- `post_issue_comment.sh` - Post comment to GitHub issue
- `post_pr_comment.sh` - Post comment to GitHub PR

See examples.md for complete workflow examples, troubleshooting, and integration patterns.

## Response Posting

### Post Comment to Issue

```bash
.claude/skills/github-operations/scripts/post_issue_comment.sh \
    owner \
    repo \
    123 \
    "## Analysis\n\nFound the issue in auth.py line 45..."
```

### Post Comment to PR

```bash
.claude/skills/github-operations/scripts/post_pr_comment.sh \
    owner \
    repo \
    456 \
    "## PR Review\n\nLooks good! Minor suggestions..."
```

## Intelligent Code Analysis Workflows

### Complexity-Based Repository Access

Automatically choose between API fetch (fast) vs. full clone (comprehensive) based on task complexity.

```bash
# Analyze task complexity
DECISION=$(.claude/skills/github-operations/scripts/analyze_complexity.sh "search for config file")
echo $DECISION  # Output: "api" (simple task, use API)

DECISION=$(.claude/skills/github-operations/scripts/analyze_complexity.sh "refactor authentication module")
echo $DECISION  # Output: "clone" (complex task, needs full repo)
```

### Smart Repository Management

```bash
# Clone or update repository (idempotent)
REPO_PATH=$(.claude/skills/github-operations/scripts/clone_or_fetch.sh https://github.com/owner/repo.git)
echo "Repository available at: $REPO_PATH"

# If already cloned: pulls latest changes
# If not cloned: clones to /data/workspace/repos/repo
```

### Fetch Files via API (No Clone Required)

```bash
# Quickly fetch file content without cloning
.claude/skills/github-operations/scripts/fetch_files_api.sh owner/repo path/to/file.py

# Fetch multiple files
for FILE in README.md config.yaml main.py; do
    .claude/skills/github-operations/scripts/fetch_files_api.sh owner/repo $FILE
done
```

### Create Draft Pull Requests with Analysis

```bash
# Create draft PR with analysis results
.claude/skills/github-operations/scripts/create_draft_pr.sh \
    owner/repo \
    "Fix: Authentication bug in login.py" \
    "## Analysis

    Found issue in login.py line 45:
    - Incorrect password validation
    - Missing rate limiting

    ## Changes
    - Added rate limiting
    - Fixed validation logic

    Fixes #123" \
    main \
    fix/auth-bug
```

### End-to-End Workflow Example

```bash
# 1. Analyze task complexity
TASK="Analyze authentication module and suggest improvements"
DECISION=$(.claude/skills/github-operations/scripts/analyze_complexity.sh "$TASK")

if [ "$DECISION" = "clone" ]; then
    # Complex analysis - clone full repo
    REPO_PATH=$(.claude/skills/github-operations/scripts/clone_or_fetch.sh https://github.com/owner/repo.git)
    cd $REPO_PATH
    # Perform comprehensive analysis
    grep -r "def authenticate" .
    # ... detailed analysis ...
else
    # Simple query - use API
    .claude/skills/github-operations/scripts/fetch_files_api.sh owner/repo auth/login.py
fi

# 2. Create draft PR with findings
.claude/skills/github-operations/scripts/create_draft_pr.sh \
    owner/repo \
    "Analysis: Authentication module improvements" \
    "$(cat analysis_results.md)"
```
