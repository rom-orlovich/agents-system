# Webhook Management Scripts

Command-line tools for managing webhooks in the Claude Machine system.

## Available Scripts

### 1. create_webhook.py
Create a new webhook configuration via API.

**Usage:**
```bash
python create_webhook.py \
  --provider github \
  --name "My GitHub Webhook" \
  --triggers "issues.opened,pull_request.opened" \
  --mention-tags "@agent,@codereviewer"
```

**Arguments:**
- `--provider` (required): Webhook provider (github, jira, slack, sentry)
- `--name` (required): Webhook display name
- `--triggers` (required): Comma-separated list of event triggers
- `--mention-tags` (optional): Mention tags for GitHub webhooks
- `--assignee-triggers` (optional): Assignee names for Jira webhooks

**Example:**
```bash
python create_webhook.py \
  --provider jira \
  --name "Sprint Planning Webhook" \
  --triggers "issue.updated" \
  --assignee-triggers "Agent Bot,Planning Bot"
```

### 2. test_webhook.py
Test a webhook with a sample payload.

**Usage:**
```bash
python test_webhook.py \
  --webhook-id webhook-123 \
  --event-type "issues.opened" \
  --payload-file sample.json
```

**Arguments:**
- `--webhook-id` (required): ID of the webhook to test
- `--event-type` (required): Event type to simulate
- `--payload-file` (optional): Path to JSON payload file

**Example:**
```bash
# Generate sample payload first
python generate_sample_payload.py \
  --provider github \
  --event-type issues.opened \
  --output /tmp/sample.json

# Test webhook with generated payload
python test_webhook.py \
  --webhook-id webhook-123 \
  --event-type "issues.opened" \
  --payload-file /tmp/sample.json
```

### 3. list_webhooks.py
List all configured webhooks.

**Usage:**
```bash
python list_webhooks.py [--provider github] [--enabled-only]
```

**Arguments:**
- `--provider` (optional): Filter by provider (github, jira, slack, sentry)
- `--enabled-only` (optional): Only show enabled webhooks

**Examples:**
```bash
# List all webhooks
python list_webhooks.py

# List only GitHub webhooks
python list_webhooks.py --provider github

# List only enabled webhooks
python list_webhooks.py --enabled-only
```

### 4. enable_webhook.py
Enable or disable a webhook.

**Usage:**
```bash
python enable_webhook.py --webhook-id webhook-123 --enable
python enable_webhook.py --webhook-id webhook-123 --disable
```

**Arguments:**
- `--webhook-id` (required): ID of the webhook
- `--enable` or `--disable` (required): Action to perform

**Example:**
```bash
# Disable a webhook temporarily
python enable_webhook.py --webhook-id webhook-123 --disable

# Re-enable it later
python enable_webhook.py --webhook-id webhook-123 --enable
```

### 5. delete_webhook.py
Delete a webhook by ID.

**Usage:**
```bash
python delete_webhook.py --webhook-id webhook-123 [--force]
```

**Arguments:**
- `--webhook-id` (required): ID of the webhook to delete
- `--force` (optional): Skip confirmation prompt

**Example:**
```bash
# Delete with confirmation
python delete_webhook.py --webhook-id webhook-123

# Force delete without confirmation
python delete_webhook.py --webhook-id webhook-123 --force
```

### 6. generate_sample_payload.py
Generate sample webhook payloads for testing.

**Usage:**
```bash
python generate_sample_payload.py \
  --provider github \
  --event-type issues.opened \
  --output sample.json
```

**Arguments:**
- `--provider` (optional): Webhook provider
- `--event-type` (optional): Event type to generate
- `--output` (optional): Output file path (default: stdout)
- `--list` (optional): List all available providers and event types

**Examples:**
```bash
# List all available sample payloads
python generate_sample_payload.py --list

# Generate GitHub issue payload
python generate_sample_payload.py \
  --provider github \
  --event-type issues.opened \
  --output /tmp/github-issue.json

# Print Jira comment payload to stdout
python generate_sample_payload.py \
  --provider jira \
  --event-type comment.created
```

**Available Payloads:**
- **GitHub**: issues.opened, issue_comment.created, pull_request.opened
- **Jira**: issue.created, issue.updated, comment.created
- **Slack**: app_mention, message
- **Sentry**: error.created, error.assigned

### 7. validate_webhook.py
Validate a webhook configuration before deployment.

**Usage:**
```bash
python validate_webhook.py --config webhook_config.json
```

**Arguments:**
- `--config` (required): Path to webhook configuration JSON file

**Example:**
```bash
# Create a webhook config file
cat > my_webhook.json <<EOF
{
  "name": "custom-github-webhook",
  "endpoint": "/webhooks/custom-github",
  "source": "github",
  "description": "Custom GitHub webhook for code reviews",
  "target_agent": "brain",
  "command_prefix": "@agent",
  "commands": [
    {
      "name": "review",
      "aliases": ["code-review"],
      "description": "Review code changes",
      "target_agent": "planning",
      "prompt_template": "Review this: {{issue.title}}",
      "requires_approval": false
    }
  ],
  "default_command": "review",
  "requires_signature": true,
  "signature_header": "X-Hub-Signature-256",
  "secret_env_var": "CUSTOM_WEBHOOK_SECRET"
}
EOF

# Validate the configuration
python validate_webhook.py --config my_webhook.json
```

## Environment Variables

All scripts use these environment variables:

- `API_BASE_URL`: Base URL for the API (default: `http://localhost:8000`)

**Set environment variables:**
```bash
export API_BASE_URL="https://your-machine.example.com"
```

## Common Workflows

### Creating and Testing a New Webhook

```bash
# 1. Create the webhook
python create_webhook.py \
  --provider github \
  --name "PR Review Webhook" \
  --triggers "pull_request.opened,pull_request.synchronize"

# Output will show webhook ID, e.g., webhook-abc123

# 2. Generate a sample payload
python generate_sample_payload.py \
  --provider github \
  --event-type pull_request.opened \
  --output /tmp/pr-payload.json

# 3. Test the webhook
python test_webhook.py \
  --webhook-id webhook-abc123 \
  --event-type "pull_request.opened" \
  --payload-file /tmp/pr-payload.json

# 4. Verify it's working
python list_webhooks.py --provider github
```

### Debugging a Webhook

```bash
# 1. Check if webhook exists and is enabled
python list_webhooks.py --provider github

# 2. Test with sample payload
python generate_sample_payload.py \
  --provider github \
  --event-type issues.opened \
  --output /tmp/debug.json

python test_webhook.py \
  --webhook-id webhook-123 \
  --event-type "issues.opened" \
  --payload-file /tmp/debug.json

# 3. Check logs for errors
# (Logs are in the main application)
```

### Managing Webhook Lifecycle

```bash
# Disable during maintenance
python enable_webhook.py --webhook-id webhook-123 --disable

# Perform maintenance...

# Re-enable webhook
python enable_webhook.py --webhook-id webhook-123 --enable

# If webhook is no longer needed
python delete_webhook.py --webhook-id webhook-123
```

## Integration with Webhook Generator Agent

These scripts are designed to work seamlessly with the webhook-generator agent:

```bash
# Ask the agent to create a webhook
# The agent will use these scripts to:
# 1. Validate the configuration
# 2. Create the webhook via API
# 3. Generate test payloads
# 4. Test the webhook
# 5. Provide setup instructions
```

## Error Handling

All scripts return appropriate exit codes:
- `0`: Success
- `1`: Error occurred

Check exit codes in scripts:
```bash
if python list_webhooks.py; then
  echo "Success!"
else
  echo "Failed!"
fi
```

## API Reference

All scripts interact with the webhook API at:
- `POST /api/webhooks` - Create webhook
- `GET /api/webhooks` - List webhooks
- `GET /api/webhooks/{id}` - Get webhook details
- `PATCH /api/webhooks/{id}` - Update webhook
- `DELETE /api/webhooks/{id}` - Delete webhook
- `POST /api/webhooks/test/{id}` - Test webhook

## Troubleshooting

### Connection Errors
```bash
# Verify API is running
curl http://localhost:8000/health

# Check if API_BASE_URL is correct
echo $API_BASE_URL
```

### Authentication Errors
Some webhooks require authentication. Check:
1. Environment variables are set correctly
2. Secrets are configured in the system
3. Signature headers match provider requirements

### Validation Errors
Use the validation script to check configurations:
```bash
python validate_webhook.py --config your_webhook.json
```

## Support

For more information:
- See `/app/.claude/agents/webhook-generator.md` for agent documentation
- See `/app/.claude/skills/webhook-management/reference.md` for API reference
- See `/app/core/webhook_configs.py` for built-in webhook examples
