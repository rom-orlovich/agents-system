"""Pre-built webhook templates for common use cases."""

# GitHub Issue Tracking Template
GITHUB_ISSUE_TRACKING = {
    "name": "GitHub Issue Tracker",
    "provider": "github",
    "description": "Automatically track and respond to GitHub issues",
    "commands": [
        {
            "trigger": "issues.opened",
            "action": "github_reaction",
            "template": "eyes",
            "priority": 0
        },
        {
            "trigger": "issues.opened",
            "action": "github_label",
            "template": "bot-processing, needs-triage",
            "priority": 1
        },
        {
            "trigger": "issues.opened",
            "action": "create_task",
            "agent": "planning",
            "template": "Analyze GitHub issue: {{issue.title}}\n\n{{issue.body}}",
            "priority": 2
        },
        {
            "trigger": "issues.opened",
            "action": "comment",
            "template": "🤖 **Automated Analysis Started**\n\nI've created a task to analyze this issue. I'll review the details and provide insights shortly.",
            "priority": 3
        }
    ]
}

# GitHub PR Review Template
GITHUB_PR_REVIEW = {
    "name": "GitHub PR Reviewer",
    "provider": "github",
    "description": "Automatically review pull requests",
    "commands": [
        {
            "trigger": "pull_request.opened",
            "action": "github_reaction",
            "template": "eyes",
            "priority": 0
        },
        {
            "trigger": "pull_request.opened",
            "action": "create_task",
            "agent": "executor",
            "template": "Review PR: {{pull_request.title}}\n\n{{pull_request.body}}\n\nFiles changed: {{pull_request.changed_files}}",
            "priority": 1
        },
        {
            "trigger": "pull_request.opened",
            "action": "comment",
            "template": "🔍 **PR Review Started**\n\nI've created a task to review this pull request. I'll analyze the changes and provide feedback.",
            "priority": 2
        }
    ]
}

# GitHub @mention Bot Template
GITHUB_MENTION_BOT = {
    "name": "GitHub Mention Bot",
    "provider": "github",
    "description": "Respond to @agent mentions in issues and PRs",
    "commands": [
        {
            "trigger": "issue_comment.created",
            "action": "github_reaction",
            "template": "eyes",
            "conditions": {"body": "@agent"},
            "priority": 0
        },
        {
            "trigger": "issue_comment.created",
            "action": "create_task",
            "agent": "planning",
            "template": "GitHub Issue #{{issue.number}}: {{comment.body}}",
            "conditions": {"body": "@agent"},
            "priority": 1
        },
        {
            "trigger": "issue_comment.created",
            "action": "comment",
            "template": "👋 I've received your request and created a task. I'll analyze this and get back to you shortly!",
            "conditions": {"body": "@agent"},
            "priority": 2
        }
    ]
}

# GitHub Bug Triage Template
GITHUB_BUG_TRIAGE = {
    "name": "GitHub Bug Triage",
    "provider": "github",
    "description": "Automatically triage bug reports",
    "commands": [
        {
            "trigger": "issues.labeled",
            "action": "github_reaction",
            "template": "+1",
            "conditions": {"label": "bug"},
            "priority": 0
        },
        {
            "trigger": "issues.labeled",
            "action": "github_label",
            "template": "needs-investigation, priority-high",
            "conditions": {"label": "bug"},
            "priority": 1
        },
        {
            "trigger": "issues.labeled",
            "action": "create_task",
            "agent": "planning",
            "template": "Investigate bug: {{issue.title}}\n\n{{issue.body}}\n\nReported by: {{issue.user.login}}",
            "conditions": {"label": "bug"},
            "priority": 2
        },
        {
            "trigger": "issues.labeled",
            "action": "comment",
            "template": "🐛 **Bug Report Received**\n\nThank you for reporting this bug. I've created a high-priority task to investigate.",
            "conditions": {"label": "bug"},
            "priority": 3
        }
    ]
}

# Jira Issue Sync Template
JIRA_ISSUE_SYNC = {
    "name": "Jira Issue Sync",
    "provider": "jira",
    "description": "Sync Jira issues with agent tasks",
    "commands": [
        {
            "trigger": "jira:issue_created",
            "action": "create_task",
            "agent": "planning",
            "template": "Jira Issue: {{issue.fields.summary}}\n\n{{issue.fields.description}}",
            "priority": 0
        }
    ]
}

# Slack Notification Template
SLACK_NOTIFICATIONS = {
    "name": "Slack Notifications",
    "provider": "slack",
    "description": "Respond to Slack mentions and messages",
    "commands": [
        {
            "trigger": "message.channels",
            "action": "create_task",
            "agent": "brain",
            "template": "Slack message from {{user.name}}: {{text}}",
            "conditions": {"text": "@agent"},
            "priority": 0
        },
        {
            "trigger": "message.channels",
            "action": "respond",
            "template": "Got it! I'll look into that.",
            "conditions": {"text": "@agent"},
            "priority": 1
        }
    ]
}

# All templates
WEBHOOK_TEMPLATES = {
    "github_issue_tracking": GITHUB_ISSUE_TRACKING,
    "github_pr_review": GITHUB_PR_REVIEW,
    "github_mention_bot": GITHUB_MENTION_BOT,
    "github_bug_triage": GITHUB_BUG_TRIAGE,
    "jira_issue_sync": JIRA_ISSUE_SYNC,
    "slack_notifications": SLACK_NOTIFICATIONS,
}


def get_template(template_id: str) -> dict:
    """Get webhook template by ID."""
    return WEBHOOK_TEMPLATES.get(template_id)


def list_templates(provider: str = None) -> list[dict]:
    """List available webhook templates, optionally filtered by provider."""
    templates = []
    for template_id, template in WEBHOOK_TEMPLATES.items():
        if provider is None or template["provider"] == provider:
            templates.append({
                "id": template_id,
                "name": template["name"],
                "provider": template["provider"],
                "description": template["description"],
                "commands_count": len(template["commands"])
            })
    return templates
