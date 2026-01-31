# Slack Operations Workflow

Complete workflow for handling Slack operations using MCP tools.

## Workflow Overview

```
Task Received → Process → Post Response → Handle Interactions
```

## Step-by-Step Workflow

### 1. Receive Task from Slack

**Task Metadata Required:**

```json
{
  "source": "slack",
  "source_metadata": {
    "channel_id": "C123456",
    "thread_ts": "1234567890.123456",
    "user_id": "U123456"
  }
}
```

### 2. Process Task

Execute the requested task (code analysis, bug fix, etc.)

### 3. Post Response

**Always reply in thread** using `thread_ts` from task metadata.

**Use MCP tool:**

```
slack:post_message
```

**Required Parameters:**

- `channel`: Channel ID from `source_metadata.channel_id`
- `thread_ts`: Thread timestamp from `source_metadata.thread_ts`
- `text`: Response message (markdown supported)

**Simple Response:**

```json
{
  "tool": "slack:post_message",
  "arguments": {
    "channel": "C123456",
    "thread_ts": "1234567890.123456",
    "text": "## ✅ Task Complete\n\n**Summary:** {summary}\n\n### Results\n{results}"
  }
}
```

### 4. Rich Formatting (Optional)

Use `blocks` parameter for rich formatting:

```json
{
  "tool": "slack:post_message",
  "arguments": {
    "channel": "C123456",
    "thread_ts": "1234567890.123456",
    "blocks": [
      {
        "type": "header",
        "text": {
          "type": "plain_text",
          "text": "✅ Task Complete"
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Task ID:* `{task_id}`\n*Summary:* {summary}"
        }
      }
    ]
  }
}
```

## Common Workflows

### Workflow 1: Job Start Notification

**When:** Task moves to RUNNING state (webhook tasks only)

**Use:**

```json
{
  "tool": "slack:post_message",
  "arguments": {
    "channel": "C123456",
    "text": "🚀 *Job Started*\n*Source:* {source}\n*Command:* {command}\n*Task ID:* `{task_id}`\n*Agent:* {agent}"
  }
}
```

### Workflow 2: Job Complete Notification

**When:** Task completes (success or failure)

**Success:**

```json
{
  "tool": "slack:post_message",
  "arguments": {
    "channel": "C123456",
    "text": "✅ *Task Completed*\n*Task ID:* `{task_id}`\n*Summary:* {summary}\n*Cost:* ${cost}"
  }
}
```

**Failure:**

```json
{
  "tool": "slack:post_message",
  "arguments": {
    "channel": "C123456",
    "text": "❌ *Task Failed*\n*Task ID:* `{task_id}`\n*Error:* {error_message}"
  }
}
```

### Workflow 3: Approval Needed Notification

**When:** Draft PR created, approval required

**Use blocks with interactive buttons:**

```json
{
  "tool": "slack:post_message",
  "arguments": {
    "channel": "C123456",
    "blocks": [
      {
        "type": "header",
        "text": {
          "type": "plain_text",
          "text": "📋 Plan Ready for Approval"
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*{title}*\n\n🎫 Ticket: `{ticket_id}`\n🔗 <{pr_url}|View Draft PR #{pr_number}>"
        }
      },
      {
        "type": "actions",
        "elements": [
          {
            "type": "button",
            "text": { "type": "plain_text", "text": "✅ Approve" },
            "style": "primary",
            "action_id": "approve_plan",
            "value": "{\"action\":\"approve\",\"repo\":\"{repo}\",\"pr_number\":{pr_number}}"
          },
          {
            "type": "button",
            "text": { "type": "plain_text", "text": "❌ Reject" },
            "style": "danger",
            "action_id": "reject_plan",
            "value": "{\"action\":\"reject\",\"repo\":\"{repo}\",\"pr_number\":{pr_number}}"
          }
        ]
      }
    ]
  }
}
```

### Workflow 4: Code Question Response

**When:** User asks code-related question in Slack

1. Analyze question
2. Search codebase or analyze code
3. Post answer in thread:

````json
{
  "tool": "slack:post_message",
  "arguments": {
    "channel": "C123456",
    "thread_ts": "1234567890.123456",
    "text": "## Analysis\n\n{answer}\n\n### Code Reference\n```python\n{code_snippet}\n```"
  }
}
````

## Message Formatting

**Markdown Support:**

- `*bold*` → **bold text**
- `_italic_` → _italic text_
- `` `code` `` → `inline code`
- `<@U123456>` → Mention user
- `<#C123456>` → Mention channel

**Example:**

```markdown
## ✅ Analysis Complete

Found issue in `login.py` line 45.

**Recommendation:** Add rate limiting.

<@U123456> Please review.
```

## Error Handling

**If task fails:**

1. Post error message in thread
2. Include error details and troubleshooting steps
3. Use error emoji: ❌

**See [templates.md](templates.md) for error templates.**

## Best Practices

1. **Always reply in thread** - Use `thread_ts` from task metadata
2. **Use markdown formatting** - Makes messages readable
3. **Include task context** - Task ID, summary, results
4. **Use appropriate emoji** - ✅ success, ❌ error, ⚠️ warning
5. **Keep messages concise** - Focus on key information
6. **Use blocks for rich formatting** - When interactive elements needed
7. **Mark as automated** - Include "_Automated by Claude Agent_" when appropriate

## Templates

**See [templates.md](templates.md) for complete templates** including:

- Task completion templates
- Job notification templates
- Approval request templates with blocks
- Error response templates
- MCP tool call examples
