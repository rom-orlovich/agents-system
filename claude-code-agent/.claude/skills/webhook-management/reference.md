# Webhook Management Reference

Complete API reference and configuration details for webhook management.

## API Endpoints

### Create Webhook
**POST** `/api/webhooks`

```json
{
  "provider": "github|jira|slack|sentry",
  "name": "Webhook Name",
  "enabled": true,
  "triggers": ["event.type"],
  "mention_tags": ["@agent", "@bot"],
  "assignee_triggers": ["AI Agent"]
}
```

### Update Webhook
**PUT** `/api/webhooks/{id}`

### Add Command
**POST** `/api/webhooks/{id}/commands`

### Edit Command
**PUT** `/api/webhooks/{id}/commands/{cmd_id}`

### Test Webhook
**POST** `/api/webhooks/{id}/test`

### Delete Webhook
**DELETE** `/api/webhooks/{id}`

## GitHub Webhook Configuration

### Mention Tags
Configure which @mentions trigger the bot:
- @agent
- @ai-assistant
- @bot
- Custom tags

### Trigger Events
- `issues.opened` - New issue created
- `issues.closed` - Issue closed
- `issue_comment.created` - Comment added
- `pull_request.opened` - PR created
- `pull_request.closed` - PR closed/merged

### Webhook Setup
```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "github",
    "name": "GitHub Mentions",
    "mention_tags": ["@agent", "@bot"],
    "commands": [{
      "trigger": "issue_comment.created",
      "condition": "body contains @agent",
      "action": "create_task",
      "agent": "planning"
    }]
  }'
```

## Jira Webhook Configuration

### Assignee Triggers
Configure which assignees trigger actions:
- AI Agent
- automation-bot
- Custom usernames

### Trigger Events
- `jira:issue_updated` - Issue updated
- `jira:issue_created` - Issue created
- `jira:comment_created` - Comment added
- `jira:issue_assigned` - Issue assigned

### Status Transitions
Track when issues move between statuses:
- To Do → In Progress
- In Progress → Done
- Done → Deployed

### Assignee-Based Trigger
```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "jira",
    "name": "Jira AI Agent Assignee",
    "enabled": true,
    "commands": [{
      "trigger": "jira:issue_updated",
      "conditions": [
        {"field": "assignee.displayName", "operator": "equals", "value": "AI Agent"}
      ],
      "action": "create_task",
      "agent": "planning",
      "task_template": {
        "title": "Analyze Jira Issue: {{issue.key}}",
        "description": "{{issue.fields.summary}}\n\n{{issue.fields.description}}",
        "metadata": {
          "jira_issue_key": "{{issue.key}}",
          "jira_project": "{{issue.fields.project.key}}",
          "priority": "{{issue.fields.priority.name}}"
        }
      }
    }]
  }'
```

### Status Transition Trigger
```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "jira",
    "name": "Jira Status Change Notification",
    "enabled": true,
    "commands": [{
      "trigger": "jira:issue_updated",
      "conditions": [
        {"field": "status.name", "operator": "equals", "value": "In Progress"},
        {"field": "assignee.displayName", "operator": "equals", "value": "AI Agent"}
      ],
      "action": "notify_slack",
      "slack_channel": "#ai-agent-activity",
      "message_template": "🤖 AI Agent started working on {{issue.key}}: {{issue.fields.summary}}"
    }]
  }'
```

### Comment Mention Trigger
```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "jira",
    "name": "Jira Comment Mention",
    "enabled": true,
    "commands": [{
      "trigger": "jira:comment_created",
      "conditions": [
        {"field": "comment.body", "operator": "contains", "value": "@ai-agent"}
      ],
      "action": "create_task",
      "agent": "brain",
      "task_template": {
        "title": "Respond to Jira comment on {{issue.key}}",
        "description": "User mentioned AI Agent:\n\n{{comment.body}}\n\nIssue: {{issue.fields.summary}}"
      }
    }]
  }'
```

### Jira Integration Commands
```bash
# Update issue status
jira issue move PROJ-123 "In Progress"

# Add comment to issue
jira issue comment PROJ-123 "AI Agent: Analysis complete. Created PR #456"

# Link issue to GitHub PR
jira issue link PROJ-123 --url "https://github.com/owner/repo/pull/456" --title "Fix PR"

# Get issue details
jira issue view PROJ-123 --json
```

## Slack Webhook Configuration

### Notification Channels
- `#ai-agent-activity` - Task status updates
- `#ai-agent-alerts` - Error notifications
- `#error-monitoring` - New error types
- `#critical-alerts` - Critical errors

### Task Status Notifications
```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "internal",
    "name": "Task Status to Slack",
    "enabled": true,
    "commands": [{
      "trigger": "task.started",
      "action": "notify_slack",
      "slack_channel": "#ai-agent-activity",
      "message_template": {
        "blocks": [{
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "🚀 *Task Started*\n*Agent:* {{agent_name}}\n*Task:* {{task_title}}\n*Issue:* <{{issue_url}}|{{issue_key}}>"
          }
        }]
      }
    }]
  }'
```

### Error Notifications
```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "internal",
    "name": "Error Alerts to Slack",
    "enabled": true,
    "commands": [{
      "trigger": "task.failed",
      "action": "notify_slack",
      "slack_channel": "#ai-agent-alerts",
      "message_template": {
        "blocks": [{
          "type": "header",
          "text": {"type": "plain_text", "text": "🚨 Task Failed"}
        }, {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "*Agent:* {{agent_name}}\n*Task:* {{task_title}}\n*Error:* ```{{error_message}}```"
          }
        }]
      }
    }]
  }'
```

### Slack Command Integration
```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "slack",
    "name": "Slack Command Handler",
    "enabled": true,
    "commands": [{
      "trigger": "slash_command",
      "command": "/ai-agent",
      "action": "parse_and_execute",
      "examples": [
        "/ai-agent fix PROJ-123",
        "/ai-agent status",
        "/ai-agent help"
      ]
    }]
  }'
```

## Sentry Webhook Configuration

### Error Levels
- `fatal` - Critical errors requiring immediate attention
- `error` - Standard errors
- `warning` - Warnings
- `info` - Informational

### High-Frequency Error Alert
```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "sentry",
    "name": "Sentry High-Frequency Errors",
    "enabled": true,
    "commands": [{
      "trigger": "sentry:issue.created",
      "conditions": [
        {"field": "event.count", "operator": "greater_than", "value": 10},
        {"field": "event.level", "operator": "equals", "value": "error"}
      ],
      "action": "create_task",
      "agent": "planning",
      "task_template": {
        "title": "Investigate Sentry Error: {{issue.title}}",
        "description": "**Error:** {{issue.title}}\n**Count:** {{event.count}} occurrences\n**Level:** {{event.level}}\n\n**Stack Trace:**\n```\n{{exception.stacktrace}}\n```\n\n**Sentry Link:** {{issue.url}}"
      }
    }]
  }'
```

### Critical Error Immediate Alert
```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "sentry",
    "name": "Sentry Critical Errors",
    "enabled": true,
    "commands": [{
      "trigger": "sentry:issue.created",
      "conditions": [
        {"field": "event.level", "operator": "equals", "value": "fatal"}
      ],
      "action": "notify_and_create_task",
      "slack_channel": "#critical-alerts",
      "slack_message": "🚨 *CRITICAL ERROR DETECTED*\n*Error:* {{issue.title}}\n*Environment:* {{event.environment}}\n*Sentry:* <{{issue.url}}|View in Sentry>\n\n🤖 AI Agent is investigating...",
      "agent": "planning",
      "priority": "critical"
    }]
  }'
```

### Error Rate Spike Detection
```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "sentry",
    "name": "Sentry Error Rate Spike",
    "enabled": true,
    "commands": [{
      "trigger": "sentry:metric_alert.triggered",
      "conditions": [
        {"field": "alert.rule", "operator": "contains", "value": "error_rate"}
      ],
      "action": "create_task",
      "agent": "planning"
    }]
  }'
```

### Sentry Integration Commands
```bash
# Get issue details
sentry-cli issues list --query "is:unresolved" --max 10

# Get specific issue
sentry-cli issues show ISSUE_ID

# Resolve issue
sentry-cli issues resolve ISSUE_ID

# Add comment to issue
sentry-cli issues update ISSUE_ID --comment "AI Agent: Fix deployed in PR #456"

# Get error events
sentry-cli events list --issue ISSUE_ID --max 5

# Get stack trace
sentry-cli events show EVENT_ID
```

## Message Formatting

### Slack Message Blocks

#### Success Message
```json
{
  "blocks": [{
    "type": "header",
    "text": {"type": "plain_text", "text": "✅ Task Completed"}
  }, {
    "type": "section",
    "fields": [
      {"type": "mrkdwn", "text": "*Issue:*\n<{{issue_url}}|{{issue_key}}>"},
      {"type": "mrkdwn", "text": "*Agent:*\n{{agent_name}}"},
      {"type": "mrkdwn", "text": "*Duration:*\n{{duration}}"},
      {"type": "mrkdwn", "text": "*Status:*\n✅ Success"}
    ]
  }, {
    "type": "actions",
    "elements": [{
      "type": "button",
      "text": {"type": "plain_text", "text": "View PR"},
      "url": "{{pr_url}}",
      "style": "primary"
    }]
  }]
}
```

#### Error Message
```json
{
  "blocks": [{
    "type": "header",
    "text": {"type": "plain_text", "text": "🚨 Task Failed"}
  }, {
    "type": "section",
    "text": {
      "type": "mrkdwn",
      "text": "*Issue:* <{{issue_url}}|{{issue_key}}>\n*Agent:* {{agent_name}}\n*Error:* ```{{error_message}}```"
    }
  }]
}
```

## Condition Operators

- `equals` - Exact match
- `contains` - Substring match
- `greater_than` - Numeric comparison
- `less_than` - Numeric comparison
- `regex` - Regular expression match

## Template Variables

### GitHub
- `{{issue.number}}` - Issue number
- `{{issue.title}}` - Issue title
- `{{issue.body}}` - Issue description
- `{{issue.url}}` - Issue URL
- `{{pr.number}}` - PR number
- `{{comment.body}}` - Comment text

### Jira
- `{{issue.key}}` - Issue key (PROJ-123)
- `{{issue.fields.summary}}` - Issue title
- `{{issue.fields.description}}` - Issue description
- `{{issue.fields.status.name}}` - Status
- `{{issue.fields.assignee.displayName}}` - Assignee

### Sentry
- `{{issue.id}}` - Sentry issue ID
- `{{issue.title}}` - Error title
- `{{issue.url}}` - Sentry URL
- `{{event.count}}` - Occurrence count
- `{{event.level}}` - Error level
- `{{exception.type}}` - Exception type
- `{{exception.stacktrace}}` - Stack trace
