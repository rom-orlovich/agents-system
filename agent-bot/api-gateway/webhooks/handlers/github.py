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
AGENT_LABELS = {"agent-review", "agent-fix", "agent-analyze"}


class GitHubWebhookHandler:
    async def validate(
        self, payload: bytes, headers: dict, secret: str
    ) -> bool:
        signature = headers.get("x-hub-signature-256", "")
        if not signature:
            logger.warning("github_webhook_missing_signature")
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
            raise PayloadParseError("github", f"Invalid JSON: {e}")

        event_type = headers.get("x-github-event", "unknown")
        action = data.get("action", "")
        full_event = f"{event_type}.{action}" if action else event_type

        installation_id = str(data.get("installation", {}).get("id", ""))
        repo = data.get("repository", {}).get("full_name", "")
        organization_id = repo.split("/")[0] if "/" in repo else ""

        metadata = self._extract_metadata(data, event_type)

        return WebhookPayload(
            provider="github",
            event_type=full_event,
            installation_id=installation_id,
            organization_id=organization_id,
            raw_payload=data,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata,
        )

    async def should_process(self, payload: WebhookPayload) -> bool:
        if self._has_agent_mention(payload):
            return True

        if self._has_agent_label(payload):
            return True

        if self._is_auto_review_event(payload):
            return True

        return False

    async def create_task_request(
        self, payload: WebhookPayload
    ) -> TaskCreationRequest:
        input_message = self._extract_input_message(payload)

        return TaskCreationRequest(
            provider="github",
            event_type=payload.event_type,
            installation_id=payload.installation_id,
            organization_id=payload.organization_id,
            input_message=input_message,
            source_metadata=payload.metadata,
            priority=self._determine_priority(payload),
        )

    def _extract_metadata(self, data: dict, event_type: str) -> dict[str, str]:
        metadata: dict[str, str] = {}

        repo = data.get("repository", {})
        metadata["repo"] = repo.get("full_name", "")

        if "pull_request" in data:
            pr = data["pull_request"]
            metadata["pr_number"] = str(pr.get("number", ""))
            metadata["pr_title"] = pr.get("title", "")
            metadata["pr_body"] = pr.get("body", "") or ""
            metadata["head_ref"] = pr.get("head", {}).get("ref", "")
            metadata["head_sha"] = pr.get("head", {}).get("sha", "")

        if "comment" in data:
            comment = data["comment"]
            metadata["comment_body"] = comment.get("body", "")

        if "issue" in data:
            issue = data["issue"]
            if not metadata.get("pr_number") and "pull_request" in issue:
                metadata["pr_number"] = str(issue.get("number", ""))

        return metadata

    def _has_agent_mention(self, payload: WebhookPayload) -> bool:
        comment_body = payload.metadata.get("comment_body", "")
        pr_body = payload.metadata.get("pr_body", "")

        return bool(
            AGENT_MENTION_PATTERN.search(comment_body)
            or AGENT_MENTION_PATTERN.search(pr_body)
        )

    def _has_agent_label(self, payload: WebhookPayload) -> bool:
        labels_str = payload.metadata.get("labels", "")
        labels = set(labels_str.lower().split(","))
        return bool(labels & AGENT_LABELS)

    def _is_auto_review_event(self, payload: WebhookPayload) -> bool:
        return payload.event_type == "pull_request.opened"

    def _extract_input_message(self, payload: WebhookPayload) -> str:
        comment_body = payload.metadata.get("comment_body", "")
        match = AGENT_MENTION_PATTERN.search(comment_body)
        if match:
            return match.group(1).strip()

        if payload.event_type == "pull_request.opened":
            pr_num = payload.metadata.get("pr_number")
            pr_title = payload.metadata.get("pr_title")
            return f"Review PR #{pr_num}: {pr_title}"

        return f"Process {payload.event_type}"

    def _determine_priority(self, payload: WebhookPayload) -> int:
        labels = payload.metadata.get("labels", "").lower()
        if "critical" in labels:
            return 0
        if "urgent" in labels:
            return 1
        return 2
