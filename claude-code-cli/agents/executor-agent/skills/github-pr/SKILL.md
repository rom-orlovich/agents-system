---
name: github-pr
description: GitHub Pull Request operations for executor agent
---

# GitHub PR Skill

## Purpose

Handle GitHub Pull Request operations during task execution, including updating PR descriptions, adding comments, and managing PR status.

## When to Use

- After implementing a fix
- When updating PR with implementation notes
- When adding comments about test results
- When marking PR as ready for review

## Available Scripts

### github_client.py

Located in `scripts/github_client.py`, provides GitHub API integration:

```python
from scripts.github_client import GitHubClient

client = GitHubClient()

# Create a PR
pr_url = await client.create_pr(
    repository="org/repo",
    title="Fix: Authentication bug",
    body="Implementation details...",
    head_branch="fix/task-123",
    base_branch="main",
    draft=False
)

# Update PR description
await client.update_pr(
    repository="org/repo",
    pr_number=42,
    body="## Implementation\n- Fixed validation\n- Added tests"
)

# Add comment to PR
await client.add_comment(
    repository="org/repo",
    pr_number=42,
    comment="✅ All tests pass. Ready for review."
)

# Add reaction to comment
await client.add_reaction(
    repository="org/repo",
    comment_id=123456,
    reaction="rocket"
)
```

## Process

1. Determine PR operation needed
2. Get PR details from task context
3. Execute GitHub API operation
4. Handle response and errors

## Output

Updates GitHub PRs with:
- Implementation details
- Test results
- Code review notes
- Status comments

## Examples

### Update PR After Implementation
```markdown
## Implementation Complete

### Changes Made
- Fixed authentication validation in middleware
- Added edge case handling
- Updated unit tests

### Test Results
- ✅ All 48 tests passing
- ✅ Linting passed
- ✅ Type checking passed

### Review Notes
- Ready for code review
- No breaking changes
```

### Add Status Comment
```markdown
✅ Implementation complete. All tests pass.

**Test Results**:
- Passed: 48
- Failed: 0
- Duration: 12.3s

**Linting**: Passed
**Type Checking**: Passed

This PR is ready for review.
```

### Convert Draft to Ready
```python
# Mark PR as ready for review
await client.mark_ready_for_review(
    repository="org/repo",
    pr_number=42
)
```
