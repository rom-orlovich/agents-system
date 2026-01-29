from typing import Final, List, Dict, Any
from pathlib import Path

EVENT_ISSUE_CREATED: Final[str] = "jira:issue_created"
EVENT_ISSUE_UPDATED: Final[str] = "jira:issue_updated"
EVENT_ISSUE_DELETED: Final[str] = "jira:issue_deleted"
EVENT_COMMENT_CREATED: Final[str] = "comment_created"
EVENT_COMMENT_UPDATED: Final[str] = "comment_updated"
EVENT_COMMENT_DELETED: Final[str] = "comment_deleted"

FIELD_WEBHOOK_EVENT: Final[str] = "webhookEvent"
FIELD_ISSUE: Final[str] = "issue"
FIELD_COMMENT: Final[str] = "comment"
FIELD_USER: Final[str] = "user"
FIELD_CHANGELOG: Final[str] = "changelog"
FIELD_KEY: Final[str] = "key"
FIELD_FIELDS: Final[str] = "fields"
FIELD_SUMMARY: Final[str] = "summary"
FIELD_DESCRIPTION: Final[str] = "description"
FIELD_STATUS: Final[str] = "status"
FIELD_ISSUETYPE: Final[str] = "issuetype"
FIELD_PROJECT: Final[str] = "project"
FIELD_BODY: Final[str] = "body"
FIELD_AUTHOR: Final[str] = "author"
FIELD_ACCOUNT_ID: Final[str] = "accountId"
FIELD_DISPLAY_NAME: Final[str] = "displayName"
FIELD_ACTIVE: Final[str] = "active"
FIELD_SELF: Final[str] = "self"
FIELD_ID: Final[str] = "id"
FIELD_NAME: Final[str] = "name"
FIELD_CREATED: Final[str] = "created"

ADF_TYPE_DOC: Final[str] = "doc"
ADF_TYPE_PARAGRAPH: Final[str] = "paragraph"
ADF_TYPE_TEXT: Final[str] = "text"
ADF_FIELD_TYPE: Final[str] = "type"
ADF_FIELD_CONTENT: Final[str] = "content"
ADF_FIELD_TEXT: Final[str] = "text"

REDIS_KEY_PREFIX_POSTED_COMMENT: Final[str] = "jira:posted_comment:"
REDIS_TTL_POSTED_COMMENT: Final[int] = 3600

ENV_JIRA_TOKEN: Final[str] = "JIRA_TOKEN"
ENV_JIRA_USER_EMAIL: Final[str] = "JIRA_USER_EMAIL"
ENV_JIRA_WEBHOOK_SECRET: Final[str] = "JIRA_WEBHOOK_SECRET"

PROVIDER_NAME: Final[str] = "jira"

STATUS_PROCESSED: Final[str] = "processed"
STATUS_REJECTED: Final[str] = "rejected"
STATUS_RECEIVED: Final[str] = "received"
STATUS_ERROR: Final[str] = "error"

MESSAGE_DOES_NOT_MEET_RULES: Final[str] = "Does not meet activation rules"
MESSAGE_NO_COMMAND_MATCHED: Final[str] = "No command matched - requires assignee change to AI agent or @agent prefix"

DEFAULT_EVENT_TYPE: Final[str] = "unknown"
DEFAULT_ISSUE_KEY: Final[str] = "unknown"


def _load_commands_from_config():
    """Load commands from static webhook config for export to tests."""
    try:
        from shared.machine_models import WebhookYamlConfig
        config_path = Path(__file__).parent / "config.yaml"

        if config_path.exists():
            yaml_config = WebhookYamlConfig.from_yaml_file(config_path)
            webhook_config = yaml_config.to_webhook_config()

            commands = [
                {
                    "name": cmd.name,
                    "aliases": cmd.aliases,
                    "description": cmd.description,
                    "target_agent": cmd.target_agent,
                    "prompt_template": cmd.prompt_template,
                    "requires_approval": cmd.requires_approval,
                }
                for cmd in webhook_config.commands
            ]
            return commands, webhook_config.command_prefix
    except Exception:
        pass

    return [], "@agent"


COMMANDS: List[Dict[str, Any]]
AGENT_TRIGGER_PREFIX: str
COMMANDS, AGENT_TRIGGER_PREFIX = _load_commands_from_config()
