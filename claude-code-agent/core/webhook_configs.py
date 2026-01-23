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
            prompt_template="Analyze this GitHub {{event_type}}:\n\nTitle: {{issue.title}}\nBody: {{issue.body}}\n\nRepository: {{repository.full_name}}\nIssue/PR: #{{issue.number}}",
            requires_approval=False,
        ),
        WebhookCommand(
            name="plan",
            aliases=["plan-fix", "create-plan"],
            description="Create a plan to fix an issue",
            target_agent="planning",
            prompt_template="Create a detailed plan to fix this issue:\n\n{{issue.title}}\n\n{{issue.body}}\n\nRepository: {{repository.full_name}}\nIssue: #{{issue.number}}",
            requires_approval=False,
        ),
        WebhookCommand(
            name="fix",
            aliases=["implement", "execute"],
            description="Implement a fix for an issue",
            target_agent="executor",
            prompt_template="Implement a fix for this issue:\n\n{{issue.title}}\n\n{{issue.body}}\n\nRepository: {{repository.full_name}}\nIssue: #{{issue.number}}",
            requires_approval=True,
        ),
        WebhookCommand(
            name="review",
            aliases=["code-review", "review-pr"],
            description="Review a pull request",
            target_agent="planning",
            prompt_template="Review this pull request:\n\nTitle: {{pull_request.title}}\nBody: {{pull_request.body}}\n\nRepository: {{repository.full_name}}\nPR: #{{pull_request.number}}",
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
            prompt_template="Analyze this Jira ticket:\n\nKey: {{issue.key}}\nSummary: {{issue.fields.summary}}\nDescription: {{issue.fields.description}}\n\nProject: {{issue.fields.project.name}}",
            requires_approval=False,
        ),
        WebhookCommand(
            name="plan",
            aliases=["plan-fix", "create-plan"],
            description="Create a plan to resolve a Jira ticket",
            target_agent="planning",
            prompt_template="Create a detailed plan to resolve this Jira ticket:\n\n{{issue.key}}: {{issue.fields.summary}}\n\n{{issue.fields.description}}\n\nProject: {{issue.fields.project.name}}",
            requires_approval=False,
        ),
        WebhookCommand(
            name="fix",
            aliases=["implement", "execute"],
            description="Implement a fix for a Jira ticket",
            target_agent="executor",
            prompt_template="Implement a fix for this Jira ticket:\n\n{{issue.key}}: {{issue.fields.summary}}\n\n{{issue.fields.description}}\n\nProject: {{issue.fields.project.name}}",
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
            prompt_template="User asked for help in Slack. Show available commands and how to use them.",
            requires_approval=False,
        ),
        WebhookCommand(
            name="analyze",
            aliases=["analysis"],
            description="Analyze a request from Slack",
            target_agent="brain",
            prompt_template="Analyze this Slack message:\n\n{{event.text}}\n\nUser: {{event.user}}\nChannel: {{event.channel}}",
            requires_approval=False,
        ),
        WebhookCommand(
            name="execute",
            aliases=["do", "run"],
            description="Execute a command from Slack",
            target_agent="executor",
            prompt_template="Execute this request from Slack:\n\n{{event.text}}\n\nUser: {{event.user}}\nChannel: {{event.channel}}",
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
