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
