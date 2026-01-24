---
name: webhook-management
description: Create, edit, test, and manage webhooks for GitHub, Jira, Slack, Sentry
user-invocable: true
---

Manages webhook lifecycle operations for GitHub, Jira, Slack, and Sentry providers.

## Quick Start

User invokes with: `/webhook-management create github` or similar commands.
This skill requires explicit user invocation for safety.

## Capabilities

- Create webhooks with custom configurations
- Test webhooks before deployment
- Configure triggers and conditions
- Set up notifications (Slack, email)
- Monitor webhook events

## Supported Providers

- **GitHub** - Issue events, PR events, mention triggers
- **Jira** - Issue updates, comment mentions, sprint changes
- **Slack** - Task notifications, error alerts, slash commands
- **Sentry** - Error detection, error rate spikes, new error types

## Helper Scripts

Scripts available in `scripts/` directory:
- `create_webhook.py` - Create webhooks via API
- `test_webhook.py` - Test webhooks with sample payloads

## Common Workflows

- **GitHub → Planning Agent** - Auto-create analysis task when @agent mentioned
- **Jira → Executor Agent** - Start implementation when issue assigned
- **Sentry → Investigation** - Create task when error threshold exceeded
- **Task → Slack** - Notify team when tasks start/complete/fail

## Additional Resources

- **Complete API reference and configurations**: See [reference.md](reference.md)
- **Workflow examples and setup guides**: See [examples.md](examples.md)
- **Helper scripts**: See `scripts/` directory
