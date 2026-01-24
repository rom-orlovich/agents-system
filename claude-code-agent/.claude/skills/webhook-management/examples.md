# Webhook Management Examples

Complete examples for common webhook configurations and workflows.

## GitHub Webhook Examples

### Example 1: GitHub Mention Webhook
Triggers when someone mentions @agent or @bot in an issue comment.

```python
create_webhook(
    provider="github",
    name="GitHub Mentions",
    mention_tags=["@agent", "@bot"],
    commands=[{
        "trigger": "issue_comment.created",
        "condition": "body contains @agent",
        "action": "create_task",
        "agent": "planning"
    }]
)
```

**Workflow:**
1. User comments on issue: "Hey @agent, can you fix this?"
2. Webhook fires → POST to `/api/webhooks/github`
3. System creates task for planning agent
4. Planning agent analyzes issue and creates plan

### Example 2: Auto-Assign Issues
Automatically work on issues with specific labels.

```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "github",
    "name": "Auto-Assign Bug Issues",
    "enabled": true,
    "commands": [{
      "trigger": "issues.labeled",
      "conditions": [
        {"field": "label.name", "operator": "equals", "value": "bug"},
        {"field": "label.name", "operator": "equals", "value": "ai-agent"}
      ],
      "action": "create_task",
      "agent": "planning"
    }]
  }'
```

### Example 3: PR Review Automation
Review PRs when they're opened.

```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "github",
    "name": "Auto PR Review",
    "enabled": true,
    "commands": [{
      "trigger": "pull_request.opened",
      "action": "create_task",
      "agent": "code-reviewer",
      "task_template": {
        "title": "Review PR #{{pr.number}}: {{pr.title}}",
        "description": "{{pr.body}}"
      }
    }]
  }'
```

## Jira Webhook Examples

### Example 1: Jira Assignee Webhook
Automatically start work when issue is assigned to "AI Agent".

```python
create_webhook(
    provider="jira",
    name="Jira Assignee",
    assignee_triggers=["AI Agent"],
    commands=[{
        "trigger": "issues.assigned",
        "condition": "assignee == 'AI Agent'",
        "action": "ask",
        "agent": "brain"
    }]
)
```

**Complete Workflow:**
```
1. Issue assigned to "AI Agent" in Jira
   ↓
2. Jira webhook fires → POST to /api/webhooks/jira
   ↓
3. System creates task for planning agent
   ↓
4. Planning agent:
   - Reads Jira issue details
   - Analyzes requirements
   - Creates PLAN.md
   - Updates Jira: "Analysis complete, starting implementation"
   ↓
5. Executor agent:
   - Implements fix based on plan
   - Runs tests
   - Creates PR
   - Updates Jira with PR link
   ↓
6. When PR merged:
   - Update Jira status to "Done"
   - Add comment with deployment info
```

### Example 2: Sprint Planning Automation
Track when issues move into current sprint.

```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "jira",
    "name": "Sprint Planning",
    "enabled": true,
    "commands": [{
      "trigger": "jira:issue_updated",
      "conditions": [
        {"field": "sprint.name", "operator": "equals", "value": "Current Sprint"},
        {"field": "assignee.displayName", "operator": "equals", "value": "AI Agent"}
      ],
      "action": "notify_slack",
      "slack_channel": "#sprint-planning",
      "message_template": "📋 New issue added to sprint: {{issue.key}} - {{issue.fields.summary}}"
    }]
  }'
```

### Example 3: Priority Escalation
Alert team when high-priority issues are created.

```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "jira",
    "name": "Priority Escalation",
    "enabled": true,
    "commands": [{
      "trigger": "jira:issue_created",
      "conditions": [
        {"field": "priority.name", "operator": "equals", "value": "Critical"}
      ],
      "action": "notify_and_create_task",
      "slack_channel": "#critical-issues",
      "agent": "planning",
      "priority": "critical"
    }]
  }'
```

## Slack Webhook Examples

### Example 1: Task Status Notifications
Send notifications when tasks start and complete.

**Workflow:**
```
GitHub Issue Created
   ↓
AI Agent starts work
   ↓
Slack notification: "🚀 Started working on issue #123"
   ↓
Planning phase complete
   ↓
Slack notification: "📋 Analysis complete, starting implementation"
   ↓
Implementation complete
   ↓
Slack notification: "✅ PR created: <link>"
   ↓
PR merged
   ↓
Slack notification: "🎉 Issue #123 resolved and deployed"
```

### Example 2: Error Monitoring Dashboard
Create a real-time error monitoring channel.

```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "internal",
    "name": "Error Dashboard",
    "enabled": true,
    "commands": [{
      "trigger": "error.detected",
      "action": "notify_slack",
      "slack_channel": "#error-monitoring",
      "message_template": {
        "blocks": [{
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "⚠️ *Error Detected*\n*Type:* {{error.type}}\n*Count:* {{error.count}}\n*Service:* {{service.name}}"
          }
        }, {
          "type": "actions",
          "elements": [{
            "type": "button",
            "text": {"type": "plain_text", "text": "Investigate"},
            "value": "investigate_{{error.id}}"
          }]
        }]
      }
    }]
  }'
```

### Example 3: Slash Command Integration
Allow team to trigger AI Agent from Slack.

```bash
# Setup Slack slash command: /ai-agent
# Point to: http://your-domain/api/webhooks/slack/commands

curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "slack",
    "name": "Slack Commands",
    "enabled": true,
    "commands": [{
      "trigger": "slash_command",
      "command": "/ai-agent",
      "action": "parse_and_execute"
    }]
  }'
```

**Usage:**
```
/ai-agent fix PROJ-123          # Fix Jira issue
/ai-agent review PR #456        # Review GitHub PR
/ai-agent status                # Get current status
/ai-agent help                  # Show help
```

## Sentry Webhook Examples

### Example 1: High-Frequency Error Investigation
Automatically investigate errors that occur frequently.

**Workflow:**
```
1. Production error occurs (>10 times in 1 hour)
   ↓
2. Sentry webhook fires → POST to /api/webhooks/sentry
   ↓
3. System creates task for planning agent
   ↓
4. Planning agent:
   - Analyzes Sentry stack trace
   - Identifies affected code
   - Searches for similar past issues
   - Creates PLAN.md with fix strategy
   - Updates Sentry issue with comment
   ↓
5. Executor agent:
   - Implements fix based on plan
   - Adds error handling/logging
   - Creates PR
   ↓
6. After deployment:
   - Monitor Sentry for error resolution
   - Mark Sentry issue as resolved
   - Notify team via Slack
```

### Example 2: Critical Error Response
Immediate response to critical production errors.

```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "sentry",
    "name": "Critical Error Response",
    "enabled": true,
    "commands": [{
      "trigger": "sentry:issue.created",
      "conditions": [
        {"field": "event.level", "operator": "equals", "value": "fatal"}
      ],
      "action": "multi_action",
      "actions": [
        {
          "type": "notify_slack",
          "channel": "#critical-alerts",
          "message": "🚨 CRITICAL ERROR: {{issue.title}}"
        },
        {
          "type": "create_task",
          "agent": "planning",
          "priority": "critical"
        },
        {
          "type": "page_oncall",
          "service": "production"
        }
      ]
    }]
  }'
```

### Example 3: Error Pattern Detection
Detect patterns in errors to identify systemic issues.

```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "sentry",
    "name": "Error Pattern Detection",
    "enabled": true,
    "commands": [{
      "trigger": "sentry:issue.created",
      "conditions": [
        {"field": "issue.is_new", "operator": "equals", "value": true}
      ],
      "action": "analyze_pattern",
      "analysis": {
        "check_similar_errors": true,
        "time_window": "24h",
        "threshold": 3
      }
    }]
  }'
```

## Multi-Service Integration Examples

### Example 1: Complete Issue Resolution Flow
GitHub → Jira → Sentry → Slack integration.

```
1. GitHub issue created with label "bug"
   ↓ Webhook triggers
2. Create Jira ticket automatically
   ↓
3. Assign to "AI Agent" in Jira
   ↓ Webhook triggers
4. Planning agent analyzes issue
   ↓ Slack notification
5. "🚀 Started working on PROJ-123"
   ↓
6. Executor implements fix
   ↓
7. PR created and linked to Jira
   ↓ Slack notification
8. "✅ PR #456 created"
   ↓
9. PR merged
   ↓
10. Jira status → "Done"
    ↓
11. Monitor Sentry for error resolution
    ↓ Slack notification
12. "🎉 Issue resolved, error count: 0"
```

### Example 2: Error-Driven Development
Sentry errors automatically create GitHub issues.

```bash
curl -X POST http://your-domain/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "sentry",
    "name": "Error to GitHub Issue",
    "enabled": true,
    "commands": [{
      "trigger": "sentry:issue.created",
      "conditions": [
        {"field": "event.count", "operator": "greater_than", "value": 5}
      ],
      "action": "create_github_issue",
      "github_repo": "owner/repo",
      "issue_template": {
        "title": "[Sentry] {{issue.title}}",
        "body": "**Error:** {{issue.title}}\n**Count:** {{event.count}}\n**Sentry:** {{issue.url}}\n\n**Stack Trace:**\n```\n{{exception.stacktrace}}\n```",
        "labels": ["bug", "sentry", "automated"]
      }
    }]
  }'
```

## Testing Webhooks

### Test with Sample Payload
```bash
# Create sample payload file
cat > sample_github_issue.json << 'EOF'
{
  "action": "opened",
  "issue": {
    "number": 123,
    "title": "Test Issue",
    "body": "This is a test issue @agent",
    "labels": [{"name": "bug"}]
  }
}
EOF

# Test webhook
python scripts/test_webhook.py \
  --webhook-id webhook-123 \
  --event-type "issues.opened" \
  --payload-file sample_github_issue.json
```

### Test Slack Notifications
```bash
# Test Slack message formatting
curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "#test-channel",
    "blocks": [{
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "🧪 *Test Notification*\nThis is a test message from webhook setup"
      }
    }]
  }'
```

### Test Sentry Integration
```bash
# Analyze test error
./scripts/analyze_sentry_error.sh TEST-ISSUE-ID

# Verify output
cat SENTRY_ANALYSIS.md
```

## Best Practices

1. **Start Simple** - Begin with basic webhooks, add complexity gradually
2. **Test Thoroughly** - Use test webhooks before deploying to production
3. **Monitor Performance** - Track webhook response times and success rates
4. **Handle Failures** - Implement retry logic and error notifications
5. **Document Changes** - Keep webhook configurations documented
6. **Use Templates** - Create reusable message templates
7. **Secure Webhooks** - Use webhook secrets and validate signatures
8. **Rate Limiting** - Implement rate limits to prevent abuse
9. **Logging** - Log all webhook events for debugging
10. **Version Control** - Store webhook configs in version control
