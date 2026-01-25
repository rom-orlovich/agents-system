---
name: webhook-response
description: Post analysis responses back to webhook sources (GitHub, Jira, Slack, Sentry)
user-invocable: false
---

Automatically post analysis responses back to the source that triggered the webhook.

## Purpose

After completing analysis for webhook-triggered tasks, this skill posts the response back to the original source (GitHub PR comment, Jira ticket comment, Slack thread, etc.).

## Usage

### Python API

```python
from .claude.skills.webhook_response.scripts.post_response import post_webhook_response

# Post response using task object
success = await post_webhook_response(task, analysis_result)
```

### Command Line

```bash
# Post response from files
python .claude/skills/webhook-response/scripts/post_response.py \
    github \
    task-123 \
    analysis.txt \
    payload.json
```

## Supported Sources

| Source | Target | Method |
|--------|--------|--------|
| **GitHub** | Issue/PR comment | `workflow_orchestrator.github_issue_analysis_workflow()` |
| **Jira** | Ticket comment | `workflow_orchestrator.jira_ticket_analysis_workflow()` |
| **Slack** | Thread reply | `slack_client.post_message()` |
| **Sentry** | Issue comment | `sentry_client.add_comment()` |

## Example

```python
import json
from .claude.skills.webhook_response.scripts.post_response import post_webhook_response

async def handle_webhook_task(task):
    # 1. Perform analysis
    analysis_result = "## Analysis\n\nFound 3 issues...\n\n## Recommendations\n..."
    
    # 2. Post response back to source
    success = await post_webhook_response(task, analysis_result)
    
    if success:
        print("✅ Posted analysis to webhook source")
    else:
        print("⚠️ Failed to post response")
```

## Error Handling

The script handles errors gracefully:
- Returns `False` if posting fails
- Logs errors with `structlog`
- Does not raise exceptions (safe to use without try/catch)

## When to Use

✅ **Use this skill when:**
- Task was triggered by a webhook (`task.source == "webhook"`)
- Analysis is complete and ready to share
- You want to close the feedback loop with the user

❌ **Don't use when:**
- Task was triggered by UI/API (not a webhook)
- Analysis is still in progress
- Approval is required before posting

## Implementation

See `scripts/post_response.py` in this skill directory for the full implementation.
