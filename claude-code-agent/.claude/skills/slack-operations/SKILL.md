---
name: slack-operations
description: Slack API operations for messages, channels, threads, and notifications
user-invocable: false
---

Slack operations using Slack API.

## Environment
- `SLACK_BOT_TOKEN` - Slack bot token (xoxb-...)
- `SLACK_APP_TOKEN` - Slack app token (xapp-...) for socket mode

## Common Operations

### Send Messages
```bash
# Simple message
curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "C123456", "text": "Hello from agent!"}'

# Message with blocks (rich formatting)
curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C123456",
    "blocks": [{
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Deployment Complete* :white_check_mark:\nVersion 1.2.0 deployed"
      }
    }]
  }'
```

### Reply to Threads
```bash
curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C123456",
    "thread_ts": "1234567890.123456",
    "text": "Reply to thread"
  }'
```

### List Channels
```bash
curl -X GET "https://slack.com/api/conversations.list" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN"
```

### Send Direct Messages
```bash
# Open DM channel
curl -X POST https://slack.com/api/conversations.open \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"users": "U123456"}'

# Send DM
curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "D123456", "text": "Private message"}'
```

## Message Formatting

- `*bold*` - **bold text**
- `_italic_` - _italic text_
- `` `code` `` - `inline code`
- `<@U123456>` - Mention user
- `<#C123456>` - Mention channel
- `<!channel>` - Mention @channel

## Notification Templates

See examples.md for deployment notifications, error alerts, and status updates.

## Response Posting

### Post Message (Generic)

```bash
# Post to channel
.claude/skills/slack-operations/scripts/post_message.sh \
    "C123456" \
    "Hello from agent!"

# Reply to thread
.claude/skills/slack-operations/scripts/post_message.sh \
    "C123456" \
    "Thread reply content" \
    "1234567890.123456"  # thread_ts
```

### Python API

```python
from core.slack_client import slack_client

# Post message
await slack_client.post_message(
    channel="C123456",
    text="Analysis results...",
    thread_ts="1234567890.123456"  # Optional
)
```

## Agent Job Notifications

Automated notifications for Claude Code agent task lifecycle.

### Environment Variables
- `SLACK_BOT_TOKEN` - Required for API access
- `SLACK_NOTIFICATION_CHANNEL` - Target channel (default: #ai-agent-activity)
- `SLACK_NOTIFICATIONS_ENABLED` - Enable/disable notifications (default: true)

### Job Start Notifications

Sent when an agent task begins processing (webhook tasks only).

```bash
# Send job start notification
.claude/skills/slack-operations/scripts/notify_job_start.sh \
    task-123 \
    jira \
    "analyze PROJ-456" \
    planning

# Parameters:
# 1. TASK_ID - Unique task identifier
# 2. SOURCE - Task source (jira, github, sentry, etc.)
# 3. COMMAND - Command being executed
# 4. AGENT - Agent handling the task (brain, planning, executor)
```

### Job Completion Notifications

Sent when an agent task completes or fails.

```bash
# Successful completion
.claude/skills/slack-operations/scripts/notify_job_complete.sh \
    task-123 \
    completed \
    0.05 \
    "Analysis complete: Found 3 issues"

# Failed task
.claude/skills/slack-operations/scripts/notify_job_complete.sh \
    task-456 \
    failed \
    0.02 \
    "Authentication error"

# Parameters:
# 1. TASK_ID - Unique task identifier
# 2. STATUS - completed or failed
# 3. COST - Cost in USD
# 4. SUMMARY - Brief result summary
```

### Notification Flow Integration

The task worker automatically sends notifications:

1. **Pre-job notification** - When task moves to RUNNING state (webhook tasks only)
2. **Post-job notification** - When task completes (success or failure)

No manual intervention required - notifications are sent automatically for all webhook-triggered tasks (Jira, GitHub, Sentry integrations).

### Example Notification Output

```
🚀 Job Started
Source: Jira
Command: analyze PROJ-123
Task ID: task-abc123
Agent: planning

✅ Task Completed
Task ID: task-abc123
Summary: Analysis complete: Found authentication bug in login.py
Cost: $0.05
```
