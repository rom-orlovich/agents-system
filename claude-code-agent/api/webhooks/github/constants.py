from typing import Final

SIGNATURE_HEADER: Final[str] = "X-Hub-Signature-256"
SIGNATURE_PREFIX: Final[str] = "sha256="

EVENT_ISSUE_COMMENT: Final[str] = "issue_comment"
EVENT_ISSUES: Final[str] = "issues"
EVENT_PULL_REQUEST: Final[str] = "pull_request"
EVENT_PULL_REQUEST_REVIEW_COMMENT: Final[str] = "pull_request_review_comment"

ACTION_CREATED: Final[str] = "created"
ACTION_EDITED: Final[str] = "edited"
ACTION_DELETED: Final[str] = "deleted"
ACTION_OPENED: Final[str] = "opened"
ACTION_CLOSED: Final[str] = "closed"
ACTION_REOPENED: Final[str] = "reopened"
ACTION_SYNCHRONIZE: Final[str] = "synchronize"

FIELD_REPOSITORY: Final[str] = "repository"
FIELD_OWNER: Final[str] = "owner"
FIELD_NAME: Final[str] = "name"
FIELD_LOGIN: Final[str] = "login"
FIELD_ISSUE: Final[str] = "issue"
FIELD_COMMENT: Final[str] = "comment"
FIELD_PULL_REQUEST: Final[str] = "pull_request"
FIELD_SENDER: Final[str] = "sender"
FIELD_NUMBER: Final[str] = "number"
FIELD_BODY: Final[str] = "body"
FIELD_TITLE: Final[str] = "title"
FIELD_ID: Final[str] = "id"
FIELD_TYPE: Final[str] = "type"

REACTION_EYES: Final[str] = "eyes"

REDIS_KEY_PREFIX_POSTED_COMMENT: Final[str] = "github:posted_comment:"
REDIS_TTL_POSTED_COMMENT: Final[int] = 3600

ENV_GITHUB_TOKEN: Final[str] = "GITHUB_TOKEN"
ENV_GITHUB_WEBHOOK_SECRET: Final[str] = "GITHUB_WEBHOOK_SECRET"

MESSAGE_ISSUE_RESPONSE: Final[str] = "👀 I'll analyze this issue and get back to you shortly."
MESSAGE_PR_RESPONSE: Final[str] = "👀 I'll review this PR and provide feedback shortly."

STATUS_CODE_UNAUTHORIZED: Final[int] = 401

PROVIDER_NAME: Final[str] = "github"
EVENT_HEADER: Final[str] = "X-GitHub-Event"

STATUS_ACCEPTED: Final[str] = "accepted"
STATUS_REJECTED: Final[str] = "rejected"
STATUS_RECEIVED: Final[str] = "received"
STATUS_ERROR: Final[str] = "error"

MESSAGE_DOES_NOT_MEET_RULES: Final[str] = "Does not meet activation rules"
MESSAGE_NO_COMMAND_MATCHED: Final[str] = "No command matched"
MESSAGE_TASK_QUEUED: Final[str] = "Task queued for processing"
MESSAGE_IMMEDIATE_RESPONSE_FAILED: Final[str] = "Failed to send immediate response. Check GITHUB_TOKEN configuration and permissions."
ERROR_IMMEDIATE_RESPONSE_FAILED: Final[str] = "immediate_response_failed"

DEFAULT_EVENT_TYPE: Final[str] = "unknown"
