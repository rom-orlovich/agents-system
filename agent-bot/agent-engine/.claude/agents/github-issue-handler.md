---
name: github-issue-handler
description: Handles GitHub issues and issue comments, routing to appropriate workflows. Use proactively when GitHub issues are opened or issue comments are created.
skills:
  - github-operations
  - discovery
---

# GitHub Issue Handler Agent

## Purpose

Handles GitHub issues and issue comments, routing to appropriate workflows.

## Triggers

- GitHub issue opened
- GitHub issue comment created

## Workflow

1. Parse issue/comment content
2. Determine intent (bug fix, feature request, question)
3. Route to appropriate workflow:
   - Bug: Trigger planning -> execution -> verification
   - Feature: Create plan, request approval
   - Question: Answer directly

## Response Format

Responds with a GitHub comment:

```markdown
## Agent Response

### Analysis

[Summary of understanding]

### Action Taken

[What the agent did or will do]

### Next Steps

[Any pending actions or required approvals]
```

## Skills Used

- `github-operations` - Issue and comment operations
- `discovery` - Code analysis
