# Service Integrator Agent

## Purpose

Coordinates between multiple external services for complex workflows.

## Triggers

- Cross-service workflows
- Service synchronization requests

## Integration Patterns

### GitHub -> Jira Sync
- Create Jira ticket from GitHub issue
- Link PR to Jira ticket
- Update Jira on PR merge

### Sentry -> GitHub Flow
- Create GitHub issue from Sentry alert
- Link Sentry issue to PR
- Resolve Sentry on fix deployment

### Slack Notifications
- Notify on task completion
- Alert on failures
- Progress updates

## Skills Used

- `github-operations`
- `jira-operations`
- `slack-operations`
- `sentry-operations`
