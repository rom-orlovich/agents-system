"""Unified response posting dispatcher.

Brain agent uses this to post responses back to webhook sources.
Delegates to domain-specific handlers.
"""

from typing import Protocol, Any
import structlog

from api.webhooks.github.handlers import GitHubResponseHandler
from api.webhooks.github.models import GitHubRoutingMetadata
from api.webhooks.jira.handlers import JiraResponseHandler
from api.webhooks.jira.models import JiraRoutingMetadata
from api.webhooks.slack.handlers import SlackResponseHandler
from api.webhooks.slack.models import SlackRoutingMetadata

logger = structlog.get_logger()


class ResponseHandler(Protocol):
    async def post_response(self, routing: Any, result: str) -> bool:
        ...


class ResponsePoster:
    def __init__(self) -> None:
        self._handlers: dict[str, ResponseHandler] = {
            "github": GitHubResponseHandler(),
            "jira": JiraResponseHandler(),
            "slack": SlackResponseHandler(),
        }

    async def post(self, source_metadata: dict, result: str) -> bool:
        webhook_source = source_metadata.get("webhook_source", "")
        routing_dict = source_metadata.get("routing", {})

        if not routing_dict and "payload" in source_metadata:
            from core.routing_metadata import extract_routing_metadata
            routing_dict = extract_routing_metadata(webhook_source, source_metadata["payload"])

        handler = self._handlers.get(webhook_source)
        if not handler:
            logger.warning("unknown_webhook_source", source=webhook_source)
            return False

        try:
            routing = self._convert_routing(webhook_source, routing_dict)
            return await handler.post_response(routing, result)
        except Exception as e:
            logger.error("response_post_failed", source=webhook_source, error=str(e))
            return False

    def _convert_routing(self, webhook_source: str, routing_dict: dict) -> Any:
        if webhook_source == "github":
            return GitHubRoutingMetadata(
                owner=routing_dict.get("owner", ""),
                repo=routing_dict.get("repo", ""),
                issue_number=routing_dict.get("issue_number"),
                pr_number=routing_dict.get("pr_number"),
                comment_id=routing_dict.get("comment_id"),
                sender=routing_dict.get("sender"),
            )
        elif webhook_source == "jira":
            return JiraRoutingMetadata(
                issue_key=routing_dict.get("ticket_key") or routing_dict.get("issue_key", ""),
                project_key=routing_dict.get("project_key", ""),
                comment_id=routing_dict.get("comment_id"),
                user_name=routing_dict.get("user_name"),
            )
        elif webhook_source == "slack":
            return SlackRoutingMetadata(
                channel_id=routing_dict.get("channel_id", ""),
                team_id=routing_dict.get("team_id", ""),
                user_id=routing_dict.get("user_id"),
                user_name=routing_dict.get("user_name"),
                thread_ts=routing_dict.get("thread_ts"),
            )
        else:
            raise ValueError(f"Unknown webhook source: {webhook_source}")


response_poster = ResponsePoster()


async def post_response(source_metadata: dict, result: str) -> bool:
    return await response_poster.post(source_metadata, result)
