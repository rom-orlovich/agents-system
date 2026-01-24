# Intelligent Code Analysis Workflows

This document describes the intelligent workflow orchestration system for automated code analysis, PR creation, and cross-service coordination.

## Overview

The system enables intelligent automation across Jira, GitHub, Slack, and Sentry for:
- Automated code analysis when Jira tickets are assigned
- Draft PR creation with automatic linking back to Jira
- Real-time Slack notifications throughout the workflow
- Cross-service coordination and error tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Intelligent Workflow Engine                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│   │ Jira Client  │      │GitHub Client │      │ Slack Client │  │
│   │              │      │              │      │              │  │
│   │ - Comments   │      │ - Issues     │      │ - Messages   │  │
│   │ - Tickets    │      │ - PRs        │      │ - Threads    │  │
│   │ - Links      │      │ - Code Search│      │ - Workflows  │  │
│   └──────────────┘      └──────────────┘      └──────────────┘  │
│                                                                   │
│   ┌──────────────┐      ┌──────────────────────────────────┐    │
│   │Sentry Client │      │   Workflow Orchestrator          │    │
│   │              │      │                                  │    │
│   │ - Errors     │      │ - Jira Analysis Workflow         │    │
│   │ - Events     │      │ - Jira + PR Workflow             │    │
│   │ - Resolution │      │ - GitHub Analysis Workflow       │    │
│   └──────────────┘      │ - Automated Notifications        │    │
│                         └──────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Service Clients

### 1. Jira Client (`core/jira_client.py`)

**Purpose:** Interact with Jira API for ticket management and workflow automation.

**Features:**
- Post comments to issues
- Get issue details
- Update issue fields
- Transition issues
- Add remote links (e.g., GitHub PRs)
- Assign issues

**Usage:**
```python
from core.jira_client import jira_client

# Post analysis comment
await jira_client.post_comment(
    issue_key="PROJ-123",
    comment_text="Analysis results..."
)

# Link GitHub PR to Jira
await jira_client.add_remote_link(
    issue_key="PROJ-123",
    url="https://github.com/owner/repo/pull/456",
    title="Fix for PROJ-123",
    relationship="fixes"
)
```

**Configuration:**
- `JIRA_URL`: Jira instance URL
- `JIRA_EMAIL`: Jira user email
- `JIRA_API_TOKEN`: Jira API token

### 2. GitHub Client (`core/github_client.py`)

**Purpose:** Interact with GitHub API for repository operations and code analysis.

**Features:**
- Post comments to issues and PRs
- Create pull requests
- Add reactions
- Update labels
- Get repository info and languages
- Search code
- Get issue details

**Usage:**
```python
from core.github_client import github_client

# Post analysis to GitHub issue
await github_client.post_issue_comment(
    repo_owner="owner",
    repo_name="repo",
    issue_number=123,
    comment_body="Analysis results..."
)

# Create draft PR
pr_data = await github_client.create_pull_request(
    repo_owner="owner",
    repo_name="repo",
    title="Fix: Issue #123",
    head="feature-branch",
    base="main",
    body="Automated fix for issue #123",
    draft=True
)
```

**Configuration:**
- `GITHUB_TOKEN`: GitHub personal access token

### 3. Slack Client (`core/slack_client.py`)

**Purpose:** Send notifications and updates to Slack channels.

**Features:**
- Post messages to channels
- Send ephemeral messages
- Add reactions
- Update messages
- Send workflow notifications with status formatting

**Usage:**
```python
from core.slack_client import slack_client

# Send workflow notification
await slack_client.send_workflow_notification(
    channel="#ai-agent-activity",
    workflow_name="Jira Analysis: PROJ-123",
    status="completed",
    details={
        "Issue": "PROJ-123",
        "Status": "Analysis posted"
    }
)
```

**Configuration:**
- `SLACK_BOT_TOKEN`: Slack bot token
- `SLACK_NOTIFICATION_CHANNEL`: Default notification channel (default: `#ai-agent-activity`)

### 4. Sentry Client (`core/sentry_client.py`)

**Purpose:** Interact with Sentry API for error tracking and monitoring.

**Features:**
- Get issue and event details
- Update issues and add comments
- Resolve issues
- Get stacktraces

**Usage:**
```python
from core.sentry_client import sentry_client

# Get error details
issue = await sentry_client.get_issue(issue_id="12345")

# Resolve with comment
await sentry_client.resolve_issue(
    issue_id="12345",
    comment="Fixed in PR #456"
)
```

**Configuration:**
- `SENTRY_AUTH_TOKEN`: Sentry authentication token
- `SENTRY_ORG_SLUG`: Sentry organization slug

## Workflow Orchestrator

**Module:** `core/workflow_orchestrator.py`

The workflow orchestrator coordinates complex multi-service workflows with automatic notifications.

### Available Workflows

#### 1. Jira Ticket Analysis Workflow

**Purpose:** Analyze Jira ticket and post results back to Jira with Slack notifications.

**Flow:**
1. Send Slack notification (workflow started)
2. Post analysis to Jira ticket
3. Send Slack notification (workflow completed)

**Usage:**
```python
from core.workflow_orchestrator import workflow_orchestrator

result = await workflow_orchestrator.jira_ticket_analysis_workflow(
    payload=jira_webhook_payload,
    analysis_result="Analysis from planning agent...",
    task_id="task-abc123"
)
```

**Returns:**
```python
{
    "workflow": "jira_analysis",
    "issue_key": "PROJ-123",
    "task_id": "task-abc123",
    "status": "completed",
    "steps": [
        {
            "name": "post_jira_comment",
            "status": "completed",
            "timestamp": "2026-01-24T12:00:00Z"
        }
    ]
}
```

#### 2. Jira Ticket with PR Workflow

**Purpose:** Analyze ticket, create PR, link PR back to Jira, with Slack notifications.

**Flow:**
1. Send Slack notification (workflow started)
2. Post analysis to Jira
3. Link GitHub PR to Jira (if PR exists)
4. Post PR link as Jira comment
5. Send Slack notification (workflow completed)

**Usage:**
```python
result = await workflow_orchestrator.jira_ticket_with_pr_workflow(
    payload=jira_webhook_payload,
    analysis_result="Analysis results...",
    pr_url="https://github.com/owner/repo/pull/456",
    task_id="task-abc123"
)
```

**Returns:**
```python
{
    "workflow": "jira_with_pr",
    "issue_key": "PROJ-123",
    "pr_url": "https://github.com/owner/repo/pull/456",
    "task_id": "task-abc123",
    "status": "completed",
    "steps": [
        {
            "name": "post_analysis_comment",
            "status": "completed",
            "timestamp": "2026-01-24T12:00:00Z"
        },
        {
            "name": "link_pr_to_jira",
            "status": "completed",
            "pr_url": "https://github.com/owner/repo/pull/456",
            "timestamp": "2026-01-24T12:05:00Z"
        }
    ]
}
```

#### 3. GitHub Issue Analysis Workflow

**Purpose:** Analyze GitHub issue and post results with Slack notifications.

**Flow:**
1. Send Slack notification (workflow started)
2. Post analysis to GitHub issue
3. Send Slack notification (workflow completed)

**Usage:**
```python
result = await workflow_orchestrator.github_issue_analysis_workflow(
    payload=github_webhook_payload,
    analysis_result="Analysis results...",
    task_id="task-abc123"
)
```

## End-to-End Workflow Example

### Jira Ticket Assignment → Code Analysis → PR Creation

**Scenario:** AI agent is assigned a Jira ticket to fix a bug.

**Step 1:** Jira webhook receives assignment
```
POST /webhooks/jira
{
  "webhookEvent": "jira:issue_updated",
  "issue": {
    "key": "PROJ-123",
    "fields": {
      "summary": "Fix login timeout issue",
      "assignee": {"displayName": "AI Agent"}
    }
  }
}
```

**Step 2:** Brain agent orchestrates workflow
```python
# Brain agent receives task and delegates

# 1. Use planning agent for analysis
planning_result = await delegate_to_planning_agent(
    task="Analyze PROJ-123: Fix login timeout issue"
)

# 2. Extract analysis from planning result
analysis = planning_result.get("analysis")

# 3. Execute Jira analysis workflow
await workflow_orchestrator.jira_ticket_analysis_workflow(
    payload=jira_payload,
    analysis_result=analysis,
    task_id=task_id
)
```

**Step 3:** Slack notification sent
```
🚀 Jira Analysis: PROJ-123: started
Issue: PROJ-123
Task ID: task-abc123
Summary: Fix login timeout issue
```

**Step 4:** Analysis posted to Jira
```
AI Agent Analysis:

The login timeout issue is caused by database connection pool exhaustion...

Recommended fix:
1. Increase connection pool size
2. Add retry logic
3. Implement connection timeout
```

**Step 5:** Executor creates PR (if implementation requested)
```python
# Brain delegates to executor for implementation
executor_result = await delegate_to_executor_agent(
    task="Implement fix for PROJ-123 based on analysis"
)

# Executor creates branch, commits changes, creates draft PR
pr_url = executor_result.get("pr_url")

# Execute Jira + PR workflow
await workflow_orchestrator.jira_ticket_with_pr_workflow(
    payload=jira_payload,
    analysis_result=analysis,
    pr_url=pr_url,
    task_id=task_id
)
```

**Step 6:** PR linked to Jira
```
🔧 Created draft PR: https://github.com/owner/repo/pull/456

Please review the proposed changes.
```

**Step 7:** Slack notification (workflow complete)
```
✅ Jira Fix: PROJ-123: completed
Issue: PROJ-123
PR: https://github.com/owner/repo/pull/456
Status: Analysis and PR posted to Jira
Task ID: task-abc123
```

## Integration with Brain Agent

The brain agent (`/.claude/agents/brain.md`) has been enhanced with workflow orchestration capabilities.

### Usage in Brain Agent

```python
# Import workflow orchestrator in brain context
from core.workflow_orchestrator import workflow_orchestrator

# When processing Jira webhook task
if webhook_source == "jira":
    # 1. Delegate to planning agent for analysis
    analysis_result = await delegate_to_planning_agent(task_description)

    # 2. Post analysis to Jira with notifications
    await workflow_orchestrator.jira_ticket_analysis_workflow(
        payload=source_metadata["payload"],
        analysis_result=analysis_result,
        task_id=task_id
    )

    # 3. If implementation needed, delegate to executor
    if requires_implementation:
        executor_result = await delegate_to_executor_agent(task_description)
        pr_url = executor_result.get("pr_url")

        # 4. Link PR to Jira
        if pr_url:
            await workflow_orchestrator.jira_ticket_with_pr_workflow(
                payload=source_metadata["payload"],
                analysis_result=analysis_result,
                pr_url=pr_url,
                task_id=task_id
            )
```

## Configuration

### Environment Variables

```bash
# Jira
JIRA_URL=https://your-org.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_AI_AGENT_NAME="AI Agent"

# GitHub
GITHUB_TOKEN=ghp_your_github_token

# Slack
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_NOTIFICATION_CHANNEL=#ai-agent-activity

# Sentry
SENTRY_AUTH_TOKEN=your-sentry-token
SENTRY_ORG_SLUG=your-org-slug
```

### Webhook Configuration

Webhooks are configured in `core/webhook_configs.py` with:
- Command matching (e.g., `@agent analyze`, `@agent fix`)
- Target agents (planning, executor)
- Prompt templates
- Default commands

## Best Practices

### 1. Workflow Selection

**Use `jira_ticket_analysis_workflow` when:**
- Task is analysis-only
- No code changes required
- Quick investigation needed

**Use `jira_ticket_with_pr_workflow` when:**
- Code changes are required
- PR needs to be linked back to Jira
- Full implementation workflow

**Use `github_issue_analysis_workflow` when:**
- GitHub issue needs analysis
- Cross-posting to Jira not needed
- Simple issue triage

### 2. Error Handling

All workflows include error handling and will:
- Log errors with context
- Send failure notifications to Slack
- Return status information for debugging

### 3. Slack Notifications

Notifications are sent automatically for:
- Workflow start
- Progress updates
- Completion
- Failures

Configure `SLACK_NOTIFICATION_CHANNEL` to route to appropriate channel.

### 4. GitHub Code Analysis

For code analysis, prefer:
- **Simple analysis:** Use `gh api` commands or `github_client` methods
- **Complex repos:** Consider cloning repository for thorough analysis
- **Code search:** Use `github_client.search_code()` for targeted searches

## Troubleshooting

### Common Issues

**1. Jira comments not posting**
- Check `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` are set
- Verify API token has correct permissions
- Check logs for authentication errors

**2. Slack notifications failing**
- Verify `SLACK_BOT_TOKEN` is valid
- Ensure bot has access to notification channel
- Check channel name format (`#channel-name`)

**3. GitHub API rate limits**
- Use authenticated requests (set `GITHUB_TOKEN`)
- Implement retry logic for rate limit errors
- Monitor API usage

**4. Workflow not triggering**
- Check webhook signature verification
- Verify command matching in webhook configs
- Check assignee name matches `JIRA_AI_AGENT_NAME`

## Future Enhancements

Potential improvements:
- Sentry error → automatic bug ticket creation
- GitHub PR review automation
- Cross-repository code analysis
- ML-based task prioritization
- Automated regression testing triggers
