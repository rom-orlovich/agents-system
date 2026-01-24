---
name: github-operations
description: GitHub CLI commands, API operations, and repository workflow for issues, PRs, actions, releases, and branch management
user-invocable: false
---

GitHub operations using `gh` CLI and GitHub API, including repository workflow management.

## Environment
- `GITHUB_TOKEN` - GitHub personal access token

## API Operations

### Issues
```bash
gh issue list --state open --limit 20
gh issue create --title "Bug: ..." --body "Description" --label bug
gh issue close 123 --comment "Fixed in PR #456"
gh issue list --search "is:open label:bug author:username"
```

### Pull Requests
```bash
gh pr create --title "Fix: ..." --body "Description" --base main
gh pr review 123 --approve
gh pr merge 123 --squash --delete-branch
gh pr view 123 --json state,statusCheckRollup
```

### GitHub Actions
```bash
gh run list --workflow ci.yml --limit 10
gh run view 123456
gh run rerun 123456 --failed
gh run view 123456 --log
```

### Releases
```bash
gh release create v1.0.0 --title "Release 1.0.0" --notes "Release notes"
gh release list --limit 10
gh release upload v1.0.0 ./dist/app.zip
```

### Repository Operations
```bash
gh repo view --json name,description,stargazersCount,forksCount
gh api repos/{owner}/{repo}/stats/contributors
gh api repos/{owner}/{repo}/traffic/views
gh api rate_limit
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

See examples.md for complete workflow examples, troubleshooting, and integration patterns.

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
