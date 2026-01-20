---
name: notifications
description: Send notifications to Slack about task status and approvals
---

# Notifications Skill

## Purpose

Send notifications to Slack channels and users about task status, approvals needed, and completions.

## When to Use

- After creating a plan that needs approval
- When a task fails or completes
- When sending status updates
- For approval requests via interactive buttons

## Available Scripts

### slack_client.py

Located in `scripts/slack_client.py`, provides Slack API integration:

```python
from scripts.slack_client import SlackClient

client = SlackClient()

# Send a simple message
await client.send_message(channel="engineering", text="Task completed!")

# Send an approval request with buttons
await client.send_approval_message(
    task_id="task-123",
    title="Fix authentication bug",
    pr_url="https://github.com/org/repo/pull/42",
    plan_summary="Plan summary here..."
)

# Reply in a thread
await client.reply_in_thread(
    channel="engineering",
    thread_ts="1234567890.123456",
    text="Update: Implementation in progress"
)
```

## Process

1. Determine notification type (approval, status, completion)
2. Format message with appropriate context
3. Send to configured Slack channel
4. For approval requests, include interactive buttons

## Output

Sends Slack messages with:
- Task information
- Links to PR/Jira
- Interactive approval buttons (when applicable)
- Status updates

## Examples

### Approval Request
```
🔔 New Plan Ready for Approval

**Task**: Fix authentication bug
**PR**: https://github.com/org/repo/pull/42

**Plan Summary**:
- Identify root cause in auth middleware
- Add validation for edge cases
- Update tests

[Approve] [Reject] [View Plan]
```

### Completion Notification
```
✅ Task Completed

**Task**: task-123
**Status**: COMPLETED
**Duration**: 3m 45s

PR: https://github.com/org/repo/pull/42
```

### Failure Notification
```
❌ Task Failed

**Task**: task-123
**Error**: Tests failed after implementation

View logs: [Link]
```
