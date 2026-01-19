"""Centralized constants and configuration.

All configurable values are loaded from environment variables with defaults.
This module provides type-safe access to configuration.

Usage:
    from shared.constants import BOT_CONFIG, QUEUE_CONFIG, TIMEOUT_CONFIG
    
    # Access bot tags
    for tag in BOT_CONFIG.tags:
        print(tag)
    
    # Access queue names
    queue_name = QUEUE_CONFIG.planning_queue
"""

import os
from typing import List
from pathlib import Path

from .types import BotConfiguration, QueueConfiguration, TimeoutConfiguration


def _parse_list(value: str, separator: str = ",") -> List[str]:
    """Parse comma-separated string into list.
    
    Args:
        value: Comma-separated string
        separator: Separator character
        
    Returns:
        List of stripped strings
    """
    return [item.strip() for item in value.split(separator) if item.strip()]


# =============================================================================
# BOT CONFIGURATION
# =============================================================================

BOT_CONFIG = BotConfiguration(
    tags=_parse_list(os.environ.get("BOT_TAGS", "@agent,@claude,@ai-agent")),
    name=os.environ.get("BOT_NAME", "AI Agent"),
    emoji=os.environ.get("BOT_EMOJI", "🤖"),
    github_username=os.environ.get("GITHUB_BOT_USERNAME", "ai-agent[bot]"),
    jira_username=os.environ.get("JIRA_BOT_USERNAME", "ai-agent"),
    slack_user_id=os.environ.get("SLACK_BOT_USER_ID", ""),
)


# =============================================================================
# QUEUE CONFIGURATION
# =============================================================================

QUEUE_CONFIG = QueueConfiguration(
    planning_queue=os.environ.get("PLANNING_QUEUE", "planning_queue"),
    execution_queue=os.environ.get("EXECUTION_QUEUE", "execution_queue"),
    priority_queue=os.environ.get("PRIORITY_QUEUE", "priority_queue"),
)


# =============================================================================
# TIMEOUT CONFIGURATION
# =============================================================================

TIMEOUT_CONFIG = TimeoutConfiguration(
    claude_code=int(os.environ.get("CLAUDE_CODE_TIMEOUT", "300")),
    git_clone=int(os.environ.get("GIT_CLONE_TIMEOUT", "120")),
    test_run=int(os.environ.get("TEST_RUN_TIMEOUT", "600")),
    webhook_response=int(os.environ.get("WEBHOOK_RESPONSE_TIMEOUT", "3")),
)


# =============================================================================
# PATH CONSTANTS
# =============================================================================

# Claude configuration directory
CLAUDE_CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")))

# Credentials file path
CREDENTIALS_FILE = CLAUDE_CONFIG_DIR / ".credentials.json"

# MCP config file path
MCP_CONFIG_FILE = CLAUDE_CONFIG_DIR / "mcp.json"

# Skills directory
SKILLS_DIR = CLAUDE_CONFIG_DIR / "skills"

# Workspace directory for repositories
WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/workspace"))

# Prompts directory (within agent)
PROMPTS_DIR = Path(os.environ.get("PROMPTS_DIR", "/app/prompts"))

# Commands YAML directory
COMMANDS_DIR = Path(os.environ.get("COMMANDS_DIR", "/app/shared/commands"))


# =============================================================================
# MCP CONFIGURATION
# =============================================================================

# Allowed tools for Claude Code
MCP_ALLOWED_TOOLS = os.environ.get(
    "MCP_ALLOWED_TOOLS",
    "Read,Write,Edit,Bash,mcp__github,mcp__sentry,mcp__atlassian"
)

# GitHub toolsets to enable
GITHUB_TOOLSETS = os.environ.get(
    "GITHUB_TOOLSETS",
    "default,actions,code_security"
)


# =============================================================================
# TOKEN REFRESH CONFIGURATION
# =============================================================================

# Enable automatic token refresh
TOKEN_REFRESH_ENABLED = os.environ.get("TOKEN_REFRESH_ENABLED", "true").lower() == "true"

# Minutes before expiry to trigger refresh
TOKEN_REFRESH_THRESHOLD_MINUTES = int(os.environ.get("TOKEN_REFRESH_THRESHOLD_MINUTES", "30"))

# Refresh interval in seconds (for cron)
TOKEN_REFRESH_INTERVAL = int(os.environ.get("TOKEN_REFRESH_INTERVAL", "1800"))  # 30 min

# AWS Secrets Manager secret name (production)
AWS_SECRET_NAME = os.environ.get("AWS_SECRET_NAME", "claude-code/credentials")


# =============================================================================
# ANTHROPIC OAUTH CONFIGURATION
# =============================================================================

# Anthropic OAuth token endpoint
ANTHROPIC_TOKEN_URL = os.environ.get(
    "ANTHROPIC_TOKEN_URL",
    "https://console.anthropic.com/api/oauth/token"
)

# Claude Code client ID (official)
ANTHROPIC_CLIENT_ID = os.environ.get("ANTHROPIC_CLIENT_ID", "claude-code")


# =============================================================================
# EXTERNAL SERVICES
# =============================================================================

# Redis
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://aiagent:localdev@localhost:5432/aiagent")

# GitHub
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

# Slack
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
SLACK_CHANNEL_AGENTS = os.environ.get("SLACK_CHANNEL_AGENTS", "#ai-agents")

# Jira
JIRA_URL = os.environ.get("JIRA_URL", "")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")

# Sentry
SENTRY_AUTH_TOKEN = os.environ.get("SENTRY_AUTH_TOKEN", "")
SENTRY_HOST = os.environ.get("SENTRY_HOST", "sentry.io")
SENTRY_ORG = os.environ.get("SENTRY_ORG", "")
