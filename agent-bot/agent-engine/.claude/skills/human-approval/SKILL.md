---
name: human-approval
description: Manages human approval workflow before code execution. Use when code changes require approval, creating draft PRs, or waiting for stakeholder approval before proceeding.
---

# Human Approval Skill

> No code execution without explicit human approval.

## Quick Reference

- **Templates**: See [templates.md](templates.md) for approval workflow communications

## When Required

Executor MUST wait for approval before implementation when:

- Task comes from webhook (Jira, Sentry, GitHub)
- Task is classified as COMPLEX
- PLAN.md modifies critical paths (auth, payments, data)

## Approval Flow

```
Planning creates PLAN.md
       ↓
Draft PR created (github-operations skill)
       ↓
Slack notification sent (slack-operations skill)
       ↓
WAIT for approval signal:
  - GitHub PR comment: "@agent approve" or "LGTM"
  - Slack button click
  - Jira status transition
       ↓
On approval → Executor proceeds
On rejection → Brain re-delegates to planning
```

## Creating Approval Request

### 1. Create Draft PR

Use MCP tool `github:create_pull_request` with `draft=true`:

See [github-operations/flow.md](../github-operations/flow.md) for complete workflow.

PR body must include:

- Summary of PLAN.md
- List of files to be modified
- Risk assessment
- Estimated changes

### 2. Send Slack Notification

Use MCP tool `slack:post_message` with approval blocks:

See [slack-operations/flow.md](../slack-operations/flow.md) for complete workflow.

Message includes:

- Ticket/issue reference
- Link to Draft PR
- Approve/Reject buttons

### 3. Update Jira (if applicable)

Post comment with:

- Link to Draft PR
- Summary of planned changes
- Request for approval

## Approval Signals

| Source    | Approve                          | Reject                  |
| --------- | -------------------------------- | ----------------------- |
| GitHub PR | `@agent approve`, `LGTM`, `:+1:` | `@agent reject`, `:-1:` |
| Slack     | Approve button                   | Reject button           |
| Jira      | Status → "Approved"              | Status → "Rejected"     |

## Check Approval Status

Before executor starts, verify:

```bash
# Check if approval exists
gh pr view $PR_NUMBER --json comments,reviews | \
  jq '.reviews[].state == "APPROVED" or
      (.comments[].body | contains("@agent approve") or contains("LGTM"))'
```

## Blocking Executor

If no approval found:

```
BLOCKED: Awaiting human approval

Draft PR: https://github.com/org/repo/pull/123
Slack notification sent to: #channel

To approve:
  - Comment "@agent approve" on PR
  - Click Approve button in Slack
  - Transition Jira to "Approved"
```

## Timeout Handling

| Duration | Action                        |
| -------- | ----------------------------- |
| 4 hours  | Send reminder notification    |
| 24 hours | Escalate to team lead         |
| 72 hours | Auto-close with "stale" label |

## Safety

- Never bypass approval for webhook tasks
- Log all approval/rejection events
- Preserve audit trail in PR comments
