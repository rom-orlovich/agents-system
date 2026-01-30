import hmac
import hashlib
import json
from datetime import datetime, timezone

import structlog

from ..registry.protocol import (
    WebhookPayload,
    TaskCreationRequest,
    PayloadParseError,
)

logger = structlog.get_logger()

SEVERITY_PRIORITY_MAP = {
    "fatal": 0,
    "error": 1,
    "warning": 2,
    "info": 3,
    "debug": 4,
}


class SentryWebhookHandler:
    async def validate(
        self, payload: bytes, headers: dict, secret: str
    ) -> bool:
        signature = headers.get("sentry-hook-signature", "")
        if not signature:
            logger.warning("sentry_webhook_missing_signature")
            return False

        expected = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    async def parse(
        self, payload: bytes, headers: dict
    ) -> WebhookPayload:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise PayloadParseError("sentry", f"Invalid JSON: {e}")

        action = data.get("action", "unknown")
        event_type = f"sentry.{action}"

        installation = data.get("installation", {})
        installation_id = str(installation.get("uuid", ""))

        project = data.get("data", {}).get("issue", {}).get("project", {})
        organization_id = project.get("slug", "")

        metadata = self._extract_metadata(data, action)

        return WebhookPayload(
            provider="sentry",
            event_type=event_type,
            installation_id=installation_id,
            organization_id=organization_id,
            raw_payload=data,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata,
        )

    async def should_process(self, payload: WebhookPayload) -> bool:
        if self._is_critical_error(payload):
            return True

        if self._is_new_issue(payload):
            return True

        return False

    async def create_task_request(
        self, payload: WebhookPayload
    ) -> TaskCreationRequest:
        input_message = self._extract_input_message(payload)

        return TaskCreationRequest(
            provider="sentry",
            event_type=payload.event_type,
            installation_id=payload.installation_id,
            organization_id=payload.organization_id,
            input_message=input_message,
            source_metadata=payload.metadata,
            priority=self._determine_priority(payload),
        )

    def _extract_metadata(self, data: dict, action: str) -> dict[str, str]:
        metadata: dict[str, str] = {}

        issue_data = data.get("data", {}).get("issue", {})
        event = data.get("data", {}).get("event", {})

        metadata["issue_id"] = str(issue_data.get("id", ""))
        metadata["issue_title"] = issue_data.get("title", "")
        metadata["issue_url"] = issue_data.get("web_url", "")
        metadata["level"] = issue_data.get("level", "error")
        metadata["culprit"] = issue_data.get("culprit", "")

        metadata["event_id"] = event.get("event_id", "")
        metadata["message"] = event.get("message", "")

        tags = event.get("tags", [])
        if tags:
            tag_dict = {tag[0]: tag[1] for tag in tags if len(tag) >= 2}
            metadata["environment"] = tag_dict.get("environment", "")
            metadata["release"] = tag_dict.get("release", "")

        exceptions = event.get("exception", {}).get("values", [])
        if exceptions:
            first_exc = exceptions[0]
            metadata["exception_type"] = first_exc.get("type", "")
            metadata["exception_value"] = first_exc.get("value", "")

            stacktrace = first_exc.get("stacktrace", {})
            frames = stacktrace.get("frames", [])
            if frames:
                last_frame = frames[-1]
                metadata["filename"] = last_frame.get("filename", "")
                metadata["function"] = last_frame.get("function", "")
                metadata["lineno"] = str(last_frame.get("lineno", ""))

        project = issue_data.get("project", {})
        metadata["project_slug"] = project.get("slug", "")
        metadata["project_name"] = project.get("name", "")

        return metadata

    def _is_critical_error(self, payload: WebhookPayload) -> bool:
        level = payload.metadata.get("level", "").lower()
        return level in ["fatal", "error"]

    def _is_new_issue(self, payload: WebhookPayload) -> bool:
        return payload.event_type in [
            "sentry.created",
            "sentry.issue.created"
        ]

    def _extract_input_message(self, payload: WebhookPayload) -> str:
        issue_title = payload.metadata.get("issue_title", "")
        exception_type = payload.metadata.get("exception_type", "")
        level = payload.metadata.get("level", "error")

        if exception_type:
            return f"Investigate {level}: {exception_type} - {issue_title}"

        return f"Investigate {level}: {issue_title}"

    def _determine_priority(self, payload: WebhookPayload) -> int:
        level = payload.metadata.get("level", "error").lower()
        return SEVERITY_PRIORITY_MAP.get(level, 2)
