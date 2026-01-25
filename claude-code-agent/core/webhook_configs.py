"""Hard-coded webhook configurations aligned with OLD Claude Code CLI structure."""

from typing import List
from shared.machine_models import WebhookConfig, WebhookCommand

# =============================================================================
# GITHUB WEBHOOK CONFIGURATION
# =============================================================================

GITHUB_WEBHOOK: WebhookConfig = WebhookConfig(
    name="github",
    endpoint="/webhooks/github",
    source="github",
    description="GitHub webhook for issues, PRs, and comments",
    target_agent="brain",
    command_prefix="@agent",
    commands=[
        WebhookCommand(
            name="analyze",
            aliases=["analysis", "analyze-issue"],
            description="Analyze an issue or PR",
            target_agent="planning",
            prompt_template="""Analyze GitHub {{event_type}} #{{issue.number}} in repository {{repository.full_name}}.

Title: {{issue.title}}

1. Use the github-operations skill to fetch full details if needed.
2. Perform comprehensive analysis.
3. Save analysis to a file (e.g., analysis.md).
4. Post the analysis back to the issue:
   python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} analysis.md""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="plan",
            aliases=["plan-fix", "create-plan"],
            description="Create a plan to fix an issue",
            target_agent="planning",
            prompt_template="""Create a detailed plan to fix issue #{{issue.number}} in repository {{repository.full_name}}.

Title: {{issue.title}}

1. Use the github-operations skill to fetch details.
2. Create the plan.
3. Save plan to a file (e.g., plan.md).
4. Post the plan back to the issue:
   python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} plan.md""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="fix",
            aliases=["implement", "execute"],
            description="Implement a fix for an issue",
            target_agent="executor",
            prompt_template="""Implement a fix for issue #{{issue.number}} in repository {{repository.full_name}}.

Title: {{issue.title}}

1. Implement the fix.
2. Summarize what was done in a file (e.g., summary.md).
3. Post the summary back to the issue:
   python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{issue.number}} summary.md""",
            requires_approval=True,
        ),
        WebhookCommand(
            name="review",
            aliases=["code-review", "review-pr"],
            description="Review a pull request",
            target_agent="planning",
            prompt_template="""Review pull request #{{pull_request.number}} in repository {{repository.full_name}}.

Title: {{pull_request.title}}

1. Use github-operations skill to fetch PR details:
   python .claude/skills/github-operations/scripts/review_pr.py {{repository.owner.login}} {{repository.name}} {{pull_request.number}}

2. Analyze the PR and generate a comprehensive review.

3. Save review to a file (e.g., review.md).

4. Post the review back to the PR:
   python .claude/skills/github-operations/scripts/post_comment.py {{repository.owner.login}} {{repository.name}} {{pull_request.number}} review.md""",
            requires_approval=False,
        ),
    ],
    default_command="analyze",
    requires_signature=True,
    signature_header="X-Hub-Signature-256",
    secret_env_var="GITHUB_WEBHOOK_SECRET",
    is_builtin=True,
)

# =============================================================================
# JIRA WEBHOOK CONFIGURATION
# =============================================================================

JIRA_WEBHOOK: WebhookConfig = WebhookConfig(
    name="jira",
    endpoint="/webhooks/jira",
    source="jira",
    description="Jira webhook for issue updates and comments",
    target_agent="brain",
    command_prefix="@agent",
    commands=[
        WebhookCommand(
            name="analyze",
            aliases=["analysis", "analyze-ticket"],
            description="Analyze a Jira ticket",
            target_agent="planning",
            prompt_template="""Analyze this Jira ticket:

Key: {{issue.key}}
Summary: {{issue.fields.summary}}
Description: {{issue.fields.description}}

Project: {{issue.fields.project.name}}

1. Perform analysis.
2. Save to file (e.g., analysis.md).
3. Post analysis back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} analysis.md""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="plan",
            aliases=["plan-fix", "create-plan"],
            description="Create a plan to resolve a Jira ticket",
            target_agent="planning",
            prompt_template="""Create a detailed plan to resolve this Jira ticket:

{{issue.key}}: {{issue.fields.summary}}

{{issue.fields.description}}

Project: {{issue.fields.project.name}}

1. Create plan.
2. Save to file (e.g., plan.md).
3. Post plan back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} plan.md""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="fix",
            aliases=["implement", "execute"],
            description="Implement a fix for a Jira ticket",
            target_agent="executor",
            prompt_template="""Implement a fix for this Jira ticket:

{{issue.key}}: {{issue.fields.summary}}

{{issue.fields.description}}

Project: {{issue.fields.project.name}}

1. Implement fix.
2. Save summary to file.
3. Post summary back to Jira:
   python .claude/skills/jira-operations/scripts/post_comment.py {{issue.key}} summary.md""",
            requires_approval=True,
        ),
    ],
    default_command="analyze",
    requires_signature=True,
    signature_header="X-Jira-Signature",
    secret_env_var="JIRA_WEBHOOK_SECRET",
    is_builtin=True,
)

# =============================================================================
# SLACK WEBHOOK CONFIGURATION
# =============================================================================

SLACK_WEBHOOK: WebhookConfig = WebhookConfig(
    name="slack",
    endpoint="/webhooks/slack",
    source="slack",
    description="Slack webhook for commands and mentions",
    target_agent="brain",
    command_prefix="@agent",
    commands=[
        WebhookCommand(
            name="help",
            aliases=["commands", "what-can-you-do"],
            description="Show available commands",
            target_agent="brain",
            prompt_template="""User asked for help in Slack.

1. Generate help message with available commands.
2. Save to file.
3. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} help.md {{event.ts}}""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="analyze",
            aliases=["analysis"],
            description="Analyze a request from Slack",
            target_agent="brain",
            prompt_template="""Analyze this Slack message:

{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Perform analysis.
2. Save to file.
3. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} analysis.md {{event.ts}}""",
            requires_approval=False,
        ),
        WebhookCommand(
            name="execute",
            aliases=["do", "run"],
            description="Execute a command from Slack",
            target_agent="executor",
            prompt_template="""Execute this request from Slack:

{{event.text}}

User: {{event.user}}
Channel: {{event.channel}}

1. Execute request.
2. Save result/summary to file.
3. Post response back to Slack:
   python .claude/skills/slack-operations/scripts/post_message.py {{event.channel}} result.md {{event.ts}}""",
            requires_approval=True,
        ),
    ],
    default_command="analyze",
    requires_signature=True,
    signature_header="X-Slack-Signature",
    secret_env_var="SLACK_WEBHOOK_SECRET",
    is_builtin=True,
)

# =============================================================================
# SENTRY WEBHOOK CONFIGURATION
# =============================================================================

SENTRY_WEBHOOK: WebhookConfig = WebhookConfig(
    name="sentry",
    endpoint="/webhooks/sentry",
    source="sentry",
    description="Sentry webhook for error alerts",
    target_agent="planning",
    command_prefix="",  # Sentry doesn't use command prefix
    commands=[
        WebhookCommand(
            name="analyze-error",
            aliases=["analyze", "investigate"],
            description="Analyze a Sentry error",
            target_agent="planning",
            prompt_template="Analyze this Sentry error:\n\nTitle: {{event.title}}\nMessage: {{event.message}}\n\nLevel: {{event.level}}\nEnvironment: {{event.environment}}\n\nURL: {{event.url}}\n\nStack Trace:\n{{event.stacktrace}}",
            requires_approval=False,
        ),
        WebhookCommand(
            name="fix-error",
            aliases=["fix", "resolve"],
            description="Create a plan to fix a Sentry error",
            target_agent="planning",
            prompt_template="Create a plan to fix this Sentry error:\n\nTitle: {{event.title}}\nMessage: {{event.message}}\n\nLevel: {{event.level}}\nEnvironment: {{event.environment}}\n\nURL: {{event.url}}\n\nStack Trace:\n{{event.stacktrace}}",
            requires_approval=False,
        ),
    ],
    default_command="analyze-error",
    requires_signature=True,
    signature_header="Sentry-Hook-Signature",
    secret_env_var="SENTRY_WEBHOOK_SECRET",
    is_builtin=True,
)

# =============================================================================
# COLLECT ALL CONFIGS
# =============================================================================

WEBHOOK_CONFIGS: List[WebhookConfig] = [
    GITHUB_WEBHOOK,
    JIRA_WEBHOOK,
    SLACK_WEBHOOK,
    SENTRY_WEBHOOK,
]


# =============================================================================
# VALIDATION
# =============================================================================

def validate_webhook_configs() -> None:
    """Validate all webhook configurations at startup."""
    import structlog
    
    logger = structlog.get_logger()
    
    # Check for duplicate endpoints
    endpoints = [config.endpoint for config in WEBHOOK_CONFIGS]
    if len(endpoints) != len(set(endpoints)):
        duplicates = [ep for ep in endpoints if endpoints.count(ep) > 1]
        raise ValueError(f"Duplicate endpoints found: {duplicates}")
    
    # Check for duplicate names
    names = [config.name for config in WEBHOOK_CONFIGS]
    if len(names) != len(set(names)):
        duplicates = [n for n in names if names.count(n) > 1]
        raise ValueError(f"Duplicate names found: {duplicates}")
    
    # Validate each config (Pydantic will raise if invalid)
    for config in WEBHOOK_CONFIGS:
        # Validate endpoint pattern
        import re
        if not re.match(r"^/webhooks/[a-z0-9-]+$", config.endpoint):
            raise ValueError(f"Invalid endpoint pattern: {config.endpoint}")
        
        # Validate commands
        for cmd in config.commands:
            if not cmd.name:
                raise ValueError(f"Command in {config.name} has empty name")
            if not cmd.target_agent:
                raise ValueError(f"Command {cmd.name} in {config.name} has no target_agent")
            if not cmd.prompt_template:
                raise ValueError(f"Command {cmd.name} in {config.name} has no prompt_template")
    
    logger.info("webhook_configs_validated", count=len(WEBHOOK_CONFIGS))


def get_webhook_by_endpoint(endpoint: str) -> WebhookConfig:
    """Get webhook config by endpoint."""
    for config in WEBHOOK_CONFIGS:
        if config.endpoint == endpoint:
            return config
    raise ValueError(f"Webhook not found for endpoint: {endpoint}")
