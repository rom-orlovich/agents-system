import hmac
import hashlib
import json
import re
from datetime import datetime, timezone

import structlog

from ..registry.protocol import (
    WebhookPayload,
    TaskCreationRequest,
    PayloadParseError,
)

logger = structlog.get_logger()

AGENT_MENTION_PATTERN = re.compile(r"@agent\s+(.+?)(?:\n|$)", re.IGNORECASE)
PRIORITY_MAP = {
    "highest": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "lowest": 4,
}


class JiraWebhookHandler:
    async def validate(
        self, payload: bytes, headers: dict, secret: str
    ) -> bool:
        signature = headers.get("x-hub-signature", "")
        if not signature:
            logger.warning("jira_webhook_missing_signature")
            return False

        expected = "sha256=" + hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    async def parse(
        self, payload: bytes, headers: dict
    ) -> WebhookPayload:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise PayloadParseError("jira", f"Invalid JSON: {e}")

        webhook_event = data.get("webhookEvent", "unknown")
        issue_event_type = data.get("issue_event_type_name", "")
        event_type = webhook_event if not issue_event_type else issue_event_type

        user = data.get("user", {})
        installation_id = user.get("accountId", "")

        issue = data.get("issue", {})
        project = issue.get("fields", {}).get("project", {})
        organization_id = project.get("key", "")

        metadata = self._extract_metadata(data, webhook_event)

        return WebhookPayload(
            provider="jira",
            event_type=event_type,
            installation_id=installation_id,
            organization_id=organization_id,
            raw_payload=data,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata,
        )

    async def should_process(self, payload: WebhookPayload) -> bool:
        if self._has_agent_mention(payload):
            return True

        if self._is_agent_assigned_issue(payload):
            return True

        if self._is_critical_issue(payload):
            return True

        return False

    async def create_task_request(
        self, payload: WebhookPayload
    ) -> TaskCreationRequest:
        input_message = self._extract_input_message(payload)

        return TaskCreationRequest(
            provider="jira",
            event_type=payload.event_type,
            installation_id=payload.installation_id,
            organization_id=payload.organization_id,
            input_message=input_message,
            source_metadata=payload.metadata,
            priority=self._determine_priority(payload),
        )

    def _extract_metadata(self, data: dict, event_type: str) -> dict[str, str]:
        metadata: dict[str, str] = {}

        issue = data.get("issue", {})
        fields = issue.get("fields", {})

        metadata["issue_key"] = issue.get("key", "")
        metadata["issue_id"] = issue.get("id", "")
        metadata["issue_type"] = fields.get("issuetype", {}).get("name", "")
        metadata["summary"] = fields.get("summary", "")
        metadata["description"] = fields.get("description", "") or ""
        metadata["status"] = fields.get("status", {}).get("name", "")
        metadata["priority"] = fields.get("priority", {}).get("name", "medium")

        assignee = fields.get("assignee", {})
        if assignee:
            metadata["assignee"] = assignee.get("displayName", "")

        project = fields.get("project", {})
        metadata["project_key"] = project.get("key", "")
        metadata["project_name"] = project.get("name", "")

        comment = data.get("comment", {})
        if comment:
            metadata["comment_body"] = comment.get("body", "")
            author = comment.get("author", {})
            metadata["comment_author"] = author.get("displayName", "")

        changelog = data.get("changelog", {})
        if changelog:
            items = changelog.get("items", [])
            metadata["changelog_items"] = json.dumps(items)

        return metadata

    def _has_agent_mention(self, payload: WebhookPayload) -> bool:
        comment_body = payload.metadata.get("comment_body", "")
        description = payload.metadata.get("description", "")

        return bool(
            AGENT_MENTION_PATTERN.search(comment_body)
            or AGENT_MENTION_PATTERN.search(description)
        )

    def _is_agent_assigned_issue(self, payload: WebhookPayload) -> bool:
        assignee = payload.metadata.get("assignee", "").lower()
        return "agent" in assignee or "bot" in assignee

    def _is_critical_issue(self, payload: WebhookPayload) -> bool:
        priority = payload.metadata.get("priority", "").lower()
        issue_type = payload.metadata.get("issue_type", "").lower()
        return priority in ["highest", "high"] or issue_type == "incident"

    def _extract_input_message(self, payload: WebhookPayload) -> str:
        comment_body = payload.metadata.get("comment_body", "")
        match = AGENT_MENTION_PATTERN.search(comment_body)
        if match:
            return match.group(1).strip()

        description = payload.metadata.get("description", "")
        desc_match = AGENT_MENTION_PATTERN.search(description)
        if desc_match:
            return desc_match.group(1).strip()

        if payload.event_type in ["jira:issue_created", "issue_created"]:
            issue_key = payload.metadata.get("issue_key")
            summary = payload.metadata.get("summary")
            return f"Analyze issue {issue_key}: {summary}"

        if payload.event_type == "comment_created":
            issue_key = payload.metadata.get("issue_key")
            return f"Respond to comment on {issue_key}"

        return f"Process {payload.event_type}"

    def _determine_priority(self, payload: WebhookPayload) -> int:
        jira_priority = payload.metadata.get("priority", "medium").lower()
        return PRIORITY_MAP.get(jira_priority, 2)
