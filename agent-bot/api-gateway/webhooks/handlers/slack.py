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

AGENT_MENTION_PATTERN = re.compile(r"<@[UW][A-Z0-9]+>", re.IGNORECASE)
BOT_KEYWORDS = ["@agent", "agent:", "hey agent"]


class SlackWebhookHandler:
    async def validate(
        self, payload: bytes, headers: dict, secret: str
    ) -> bool:
        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")

        if not timestamp or not signature:
            logger.warning("slack_webhook_missing_headers")
            return False

        sig_basestring = f"v0:{timestamp}:{payload.decode()}"
        expected = "v0=" + hmac.new(
            secret.encode(), sig_basestring.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    async def parse(
        self, payload: bytes, headers: dict
    ) -> WebhookPayload:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise PayloadParseError("slack", f"Invalid JSON: {e}")

        if data.get("type") == "url_verification":
            raise PayloadParseError(
                "slack",
                "URL verification challenge should be handled separately"
            )

        event_type = data.get("type", "unknown")
        event_data = data.get("event", {})

        if event_type == "event_callback":
            event_type = event_data.get("type", "unknown")

        team_id = data.get("team_id", "")
        installation_id = team_id

        metadata = self._extract_metadata(data, event_type)

        return WebhookPayload(
            provider="slack",
            event_type=event_type,
            installation_id=installation_id,
            organization_id=team_id,
            raw_payload=data,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata,
        )

    async def should_process(self, payload: WebhookPayload) -> bool:
        if self._is_bot_message(payload):
            return False

        if self._has_bot_mention(payload):
            return True

        if self._has_bot_keyword(payload):
            return True

        if self._is_direct_message(payload):
            return True

        return False

    async def create_task_request(
        self, payload: WebhookPayload
    ) -> TaskCreationRequest:
        input_message = self._extract_input_message(payload)

        return TaskCreationRequest(
            provider="slack",
            event_type=payload.event_type,
            installation_id=payload.installation_id,
            organization_id=payload.organization_id,
            input_message=input_message,
            source_metadata=payload.metadata,
            priority=self._determine_priority(payload),
        )

    def _extract_metadata(self, data: dict, event_type: str) -> dict[str, str]:
        metadata: dict[str, str] = {}

        event = data.get("event", {})

        metadata["channel"] = event.get("channel", "")
        metadata["channel_type"] = event.get("channel_type", "")
        metadata["user"] = event.get("user", "")
        metadata["text"] = event.get("text", "")
        metadata["ts"] = event.get("ts", "")
        metadata["thread_ts"] = event.get("thread_ts", "")

        if "message" in event:
            message = event["message"]
            metadata["text"] = message.get("text", "")
            metadata["user"] = message.get("user", "")

        bot_id = event.get("bot_id", "")
        if bot_id:
            metadata["bot_id"] = bot_id

        files = event.get("files", [])
        if files:
            metadata["file_count"] = str(len(files))

        reaction = event.get("reaction", "")
        if reaction:
            metadata["reaction"] = reaction

        return metadata

    def _is_bot_message(self, payload: WebhookPayload) -> bool:
        return bool(payload.metadata.get("bot_id"))

    def _has_bot_mention(self, payload: WebhookPayload) -> bool:
        text = payload.metadata.get("text", "")
        return bool(AGENT_MENTION_PATTERN.search(text))

    def _has_bot_keyword(self, payload: WebhookPayload) -> bool:
        text = payload.metadata.get("text", "").lower()
        return any(keyword in text for keyword in BOT_KEYWORDS)

    def _is_direct_message(self, payload: WebhookPayload) -> bool:
        channel_type = payload.metadata.get("channel_type", "")
        return channel_type == "im"

    def _extract_input_message(self, payload: WebhookPayload) -> str:
        text = payload.metadata.get("text", "")

        text = AGENT_MENTION_PATTERN.sub("", text).strip()

        for keyword in BOT_KEYWORDS:
            text = text.replace(keyword, "").strip()

        if not text:
            return "How can I help you?"

        return text

    def _determine_priority(self, payload: WebhookPayload) -> int:
        channel_type = payload.metadata.get("channel_type", "")

        if channel_type == "im":
            return 1

        if payload.metadata.get("thread_ts"):
            return 2

        return 3
