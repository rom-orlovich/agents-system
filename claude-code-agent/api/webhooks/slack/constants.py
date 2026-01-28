from typing import Final

TYPE_URL_VERIFICATION: Final[str] = "url_verification"
TYPE_EVENT_CALLBACK: Final[str] = "event_callback"
TYPE_APP_MENTION: Final[str] = "app_mention"
TYPE_MESSAGE: Final[str] = "message"

FIELD_TYPE: Final[str] = "type"
FIELD_CHALLENGE: Final[str] = "challenge"
FIELD_EVENT: Final[str] = "event"
FIELD_USER: Final[str] = "user"
FIELD_TEXT: Final[str] = "text"
FIELD_TS: Final[str] = "ts"
FIELD_CHANNEL: Final[str] = "channel"
FIELD_TEAM_ID: Final[str] = "team_id"
FIELD_API_APP_ID: Final[str] = "api_app_id"
FIELD_TOKEN: Final[str] = "token"
FIELD_TEAM_DOMAIN: Final[str] = "team_domain"
FIELD_CHANNEL_ID: Final[str] = "channel_id"
FIELD_CHANNEL_NAME: Final[str] = "channel_name"
FIELD_USER_ID: Final[str] = "user_id"
FIELD_USER_NAME: Final[str] = "user_name"
FIELD_COMMAND: Final[str] = "command"
FIELD_RESPONSE_URL: Final[str] = "response_url"
FIELD_TRIGGER_ID: Final[str] = "trigger_id"
FIELD_MESSAGE: Final[str] = "message"
FIELD_ID: Final[str] = "id"
FIELD_USERNAME: Final[str] = "username"
FIELD_NAME: Final[str] = "name"
FIELD_DOMAIN: Final[str] = "domain"

PROVIDER_NAME: Final[str] = "slack"

STATUS_PROCESSED: Final[str] = "processed"
STATUS_RECEIVED: Final[str] = "received"
STATUS_REJECTED: Final[str] = "rejected"

DEFAULT_EVENT_TYPE: Final[str] = "unknown"
DEFAULT_CHANNEL: Final[str] = "unknown"

MESSAGE_NO_COMMAND_MATCHED: Final[str] = "No command matched"
MESSAGE_DOES_NOT_MEET_RULES: Final[str] = "Does not meet activation rules"

SLACK_MESSAGE_MAX_LENGTH: Final[int] = 4000

ENV_SLACK_TOKEN: Final[str] = "SLACK_BOT_TOKEN"
ENV_SLACK_SIGNING_SECRET: Final[str] = "SLACK_SIGNING_SECRET"
ENV_SLACK_CHANNEL_AGENTS: Final[str] = "SLACK_CHANNEL_AGENTS"
ENV_SLACK_CHANNEL_ERRORS: Final[str] = "SLACK_CHANNEL_ERRORS"
ENV_SLACK_NOTIFICATIONS_ENABLED: Final[str] = "SLACK_NOTIFICATIONS_ENABLED"

DEFAULT_CHANNEL_AGENTS: Final[str] = "#ai-agent-activity"
DEFAULT_CHANNEL_ERRORS: Final[str] = "#ai-agent-errors"
