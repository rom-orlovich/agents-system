# Webhook Management Skill

Manages webhook lifecycle operations.

## Capabilities

- Create webhooks with custom configurations
- Edit webhook commands and triggers
- Configure bot mention tags
- Set up assignee triggers
- Test webhooks before deployment
- Monitor webhook events
- Delete webhooks

## Scripts

### create_webhook.py
Creates a new webhook configuration.

Usage:
```bash
python create_webhook.py \
  --provider github \
  --name "GitHub Issues" \
  --triggers "issues.opened,issue_comment.created" \
  --mention-tags "@agent,@bot"
```

### edit_command.py
Edits an existing webhook command.

Usage:
```bash
python edit_command.py \
  --webhook-id webhook-123 \
  --command-id cmd-456 \
  --trigger "issues.assigned" \
  --condition "assignee:AI Agent"
```

### test_webhook.py
Tests a webhook with sample payload.

Usage:
```bash
python test_webhook.py \
  --webhook-id webhook-123 \
  --event-type "issues.opened" \
  --payload-file sample.json
```

## API Endpoints Used

- POST /api/webhooks - Create webhook
- PUT /api/webhooks/{id} - Update webhook
- POST /api/webhooks/{id}/commands - Add command
- PUT /api/webhooks/{id}/commands/{cmd_id} - Edit command
- POST /api/webhooks/{id}/test - Test webhook
- DELETE /api/webhooks/{id} - Delete webhook

## Configuration Options

### Mention Tags
Configure which @mentions trigger the bot:
- @agent
- @ai-assistant
- @bot
- Custom tags

### Assignee Triggers
Configure which assignees trigger actions:
- AI Agent
- automation-bot
- Custom usernames

### Trigger Conditions
- Event type (issues.opened, pr.created, etc.)
- Field conditions (label, status, assignee)
- Pattern matching (regex, contains, equals)

## Examples

### Example 1: GitHub Mention Webhook
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

### Example 2: Jira Assignee Webhook
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
