# Webhook Configuration Templates

Pre-built webhook configuration templates for common use cases. These templates can be customized and deployed to your Claude Machine.

## Available Templates

### 1. custom-github-webhook.json
**Advanced GitHub code review workflows**

Features:
- Detailed code reviews
- Security vulnerability scanning
- Automated PR merging with validation
- Test coverage analysis

Commands:
- `@agent review` - Perform detailed code review
- `@agent security-scan` - Run security analysis
- `@agent auto-merge` - Validate and merge PR
- `@agent test-coverage` - Analyze test coverage

**Use Case:** Teams wanting automated code quality checks and reviews on pull requests.

### 2. custom-jira-webhook.json
**Sprint planning and execution**

Features:
- Sprint planning assistance
- Effort estimation
- Task implementation
- Blocker analysis
- Retrospective generation

Commands:
- `@agent sprint-plan` - Analyze and plan sprint work
- `@agent estimate` - Provide effort estimation
- `@agent implement` - Implement ticket requirements
- `@agent block-analysis` - Analyze blockers
- `@agent retrospective` - Generate retrospective insights

**Use Case:** Agile teams using Jira for sprint planning and task management.

### 3. custom-sentry-webhook.json
**Intelligent error triage and resolution**

Features:
- Error triage and prioritization
- Root cause analysis
- Automated fix generation
- Pattern detection
- Regression checking
- Monitoring setup recommendations

Commands:
- `triage` - Triage and analyze errors (default)
- `root-cause` - Perform deep root cause analysis
- `auto-fix` - Create automated fixes
- `pattern-detection` - Detect error patterns
- `regression-check` - Check for regressions
- `monitoring-setup` - Set up monitoring

**Use Case:** DevOps teams managing production errors with Sentry.

### 4. custom-slack-webhook.json
**DevOps and incident management**

Features:
- Incident response workflow
- Deployment management
- Rollback procedures
- System status checks
- Log analysis
- Infrastructure scaling
- On-call management

Commands:
- `@devbot incident` - Start incident response
- `@devbot deploy` - Manage deployments
- `@devbot rollback` - Execute rollback
- `@devbot status` - Check system health
- `@devbot logs` - Analyze logs
- `@devbot scale` - Manage scaling
- `@devbot metrics` - Generate metrics report
- `@devbot oncall` - Manage on-call escalations

**Use Case:** DevOps teams using Slack for incident management and operations.

## How to Use Templates

### Option 1: Deploy via Validation Script

```bash
# 1. Validate the template
python /app/.claude/skills/webhook-management/scripts/validate_webhook.py \
  --config /app/.claude/skills/webhook-management/templates/custom-github-webhook.json

# 2. If valid, add to webhook_configs.py or deploy via API
```

### Option 2: Deploy via API

```bash
# Convert template to API format and deploy
# (Note: Templates need conversion from static config to API format)

# Example for GitHub webhook:
curl -X POST http://localhost:8000/api/webhooks \
  -H "Content-Type: application/json" \
  -d @custom-github-webhook.json
```

### Option 3: Use Webhook Generator Agent

```
Ask the webhook-generator agent to deploy a template:

"Use the webhook-generator agent to deploy the custom GitHub webhook template"

The agent will:
1. Read the template
2. Validate the configuration
3. Deploy via API
4. Provide setup instructions
```

## Customizing Templates

### 1. Copy Template

```bash
cp /app/.claude/skills/webhook-management/templates/custom-github-webhook.json \
   my-custom-webhook.json
```

### 2. Edit Configuration

Open `my-custom-webhook.json` and modify:

```json
{
  "name": "my-custom-webhook",           // Change webhook name
  "endpoint": "/webhooks/my-custom",     // Change endpoint
  "description": "My custom webhook",    // Update description
  "command_prefix": "@mybot",            // Change command prefix
  "commands": [
    {
      "name": "my-command",              // Add/modify commands
      "target_agent": "planning",        // Choose agent
      "prompt_template": "...",          // Customize prompt
      "requires_approval": false         // Set approval requirement
    }
  ]
}
```

### 3. Validate Customizations

```bash
python /app/.claude/skills/webhook-management/scripts/validate_webhook.py \
  --config my-custom-webhook.json
```

### 4. Test Before Deployment

```bash
# Generate sample payload
python /app/.claude/skills/webhook-management/scripts/generate_sample_payload.py \
  --provider github \
  --event-type issues.opened \
  --output test-payload.json

# Test webhook logic (after deployment)
python /app/.claude/skills/webhook-management/scripts/test_webhook.py \
  --webhook-id my-webhook-id \
  --event-type "issues.opened" \
  --payload-file test-payload.json
```

## Template Structure Explained

### WebhookConfig Fields

```json
{
  "name": "unique-webhook-name",
  // Unique identifier, alphanumeric with hyphens

  "endpoint": "/webhooks/provider-name",
  // URL endpoint, must match pattern /webhooks/[name]

  "source": "github|jira|slack|sentry|custom",
  // Provider type

  "description": "Brief description of webhook purpose",
  // Human-readable description

  "target_agent": "brain|planning|executor",
  // Default agent for routing

  "command_prefix": "@agent",
  // Prefix to detect commands (empty string for no prefix)

  "commands": [...],
  // Array of WebhookCommand objects (see below)

  "default_command": "command-name",
  // Command to use if no specific command detected

  "requires_signature": true,
  // Whether to validate webhook signatures

  "signature_header": "X-Provider-Signature",
  // HTTP header containing signature

  "secret_env_var": "PROVIDER_WEBHOOK_SECRET",
  // Environment variable with webhook secret

  "is_builtin": false
  // Whether this is a system built-in webhook
}
```

### WebhookCommand Fields

```json
{
  "name": "command-name",
  // Command name (lowercase, alphanumeric, hyphens)

  "aliases": ["alias1", "alias2"],
  // Alternative names for the command

  "description": "What this command does",
  // Human-readable description

  "target_agent": "planning|executor|brain",
  // Which agent handles this command

  "prompt_template": "Template with {{variables}}",
  // Jinja2-style template with placeholder variables

  "requires_approval": false
  // Whether command requires user approval before execution
}
```

### Available Template Variables

Variables depend on the provider. See templates for examples.

**Common Variables:**
- GitHub: `{{issue.title}}`, `{{pull_request.number}}`, `{{repository.full_name}}`
- Jira: `{{issue.key}}`, `{{issue.fields.summary}}`, `{{issue.fields.project.name}}`
- Slack: `{{event.text}}`, `{{event.user}}`, `{{event.channel}}`
- Sentry: `{{event.title}}`, `{{event.stacktrace}}`, `{{event.level}}`

## Agent Targeting Guide

### brain
- General routing and decision making
- Multi-step workflows
- Coordinating other agents
- Default for unknown commands

### planning
- Analysis and investigation
- Root cause analysis
- Planning and estimation
- Read-only operations
- Risk assessment

### executor
- Code implementation
- Deployments
- Automated fixes
- Write operations
- **Always set `requires_approval: true` for executor commands**

## Security Best Practices

### 1. Always Require Signatures

```json
{
  "requires_signature": true,
  "signature_header": "X-Provider-Signature",
  "secret_env_var": "WEBHOOK_SECRET"
}
```

### 2. Set Appropriate Approval Requirements

```json
{
  "commands": [
    {
      "name": "read-only-operation",
      "requires_approval": false  // Safe, read-only
    },
    {
      "name": "write-operation",
      "requires_approval": true   // Requires approval
    }
  ]
}
```

### 3. Use Unique Endpoints

```json
{
  "endpoint": "/webhooks/my-unique-endpoint-name"
  // Avoid predictable or generic names
}
```

### 4. Validate Input in Templates

```json
{
  "prompt_template": "Analyze issue: {{issue.title | truncate(200)}}"
  // Use template filters to sanitize input
}
```

### 5. Set Secure Environment Variables

```bash
# In your .env or system environment
export CUSTOM_WEBHOOK_SECRET="$(openssl rand -hex 32)"
export GITHUB_WEBHOOK_SECRET="your-github-secret"
```

## Provider Setup Instructions

### GitHub

1. Go to repository Settings → Webhooks → Add webhook
2. Payload URL: `https://your-machine.example.com/webhooks/custom-github`
3. Content type: `application/json`
4. Secret: Value from `GITHUB_WEBHOOK_SECRET` env var
5. Events: Select relevant events (Issues, Pull requests, etc.)
6. Active: ✓

### Jira

1. Go to Settings → System → WebHooks → Create a WebHook
2. URL: `https://your-machine.example.com/webhooks/custom-jira-sprint`
3. Events: Issue created, updated, commented, etc.
4. Configure JQL filter if needed
5. Set secret in header configuration

### Slack

1. Go to Slack App settings → Event Subscriptions
2. Request URL: `https://your-machine.example.com/webhooks/custom-slack-devops`
3. Subscribe to events: app_mention, message.channels, etc.
4. Configure slash commands if needed
5. Install app to workspace

### Sentry

1. Go to Settings → Integrations → WebHooks
2. Callback URL: `https://your-machine.example.com/webhooks/custom-sentry-triage`
3. Events: Error created, Issue assigned, etc.
4. Configure secret token
5. Save configuration

## Examples

### Creating a Custom Workflow

Combine multiple templates for comprehensive coverage:

```bash
# 1. Deploy GitHub webhook for code review
# 2. Deploy Jira webhook for task management
# 3. Deploy Slack webhook for team notifications
# 4. Deploy Sentry webhook for error handling

# Result: Complete DevOps workflow from ticket → code → deploy → monitor
```

### Chaining Commands

Design commands that work together:

1. Sentry detects error → Creates Jira ticket
2. Jira ticket assigned → Planning agent analyzes
3. Analysis complete → Executor implements fix
4. Fix deployed → GitHub PR created
5. PR merged → Slack notification sent

## Troubleshooting

### Validation Fails

```bash
# Use validation script to see specific errors
python scripts/validate_webhook.py --config your-webhook.json
```

### Command Not Triggering

Check:
1. Command prefix matches (`@agent` vs `@devbot`)
2. Command name/aliases are correct
3. Webhook is enabled
4. Provider sent correct event type

### Signature Validation Errors

Check:
1. Environment variable is set correctly
2. Secret matches provider configuration
3. Signature header name matches provider

### Template Variables Not Rendering

Check:
1. Variable names match provider payload structure
2. Payload contains expected fields
3. Use test script to see actual payload structure

## Contributing Templates

To contribute new templates:

1. Create template following structure guidelines
2. Validate template
3. Test with sample payloads
4. Document use case and commands
5. Add to this README
6. Submit for review

## Support

- Agent Documentation: `/app/.claude/agents/webhook-generator.md`
- Script Documentation: `/app/.claude/skills/webhook-management/scripts/README.md`
- API Reference: `/app/.claude/skills/webhook-management/reference.md`
- Core Configs: `/app/core/webhook_configs.py`
