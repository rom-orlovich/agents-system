"""Routing metadata dispatcher for webhook response posting.

Delegates to domain-specific extractors for routing metadata.
"""

from typing import Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from api.webhooks.github.models import GitHubRoutingMetadata
    from api.webhooks.jira.models import JiraRoutingMetadata
    from api.webhooks.slack.models import SlackRoutingMetadata


def _get_github_routing():
    from api.webhooks.github.routing import extract_github_routing
    return extract_github_routing


def _get_jira_routing():
    from api.webhooks.jira.routing import extract_jira_routing
    return extract_jira_routing


def _get_slack_routing():
    from api.webhooks.slack.routing import extract_slack_routing
    return extract_slack_routing


def extract_github_metadata(payload: dict) -> dict:
    extract_github_routing = _get_github_routing()
    routing = extract_github_routing(payload)
    result = {
        "owner": routing.owner,
        "repo": routing.repo,
    }
    if routing.issue_number:
        result["issue_number"] = routing.issue_number
    if routing.pr_number:
        result["pr_number"] = routing.pr_number
    if routing.comment_id:
        result["comment_id"] = routing.comment_id
    if routing.sender:
        result["sender"] = routing.sender
    return result


def extract_jira_metadata(payload: dict) -> dict:
    extract_jira_routing = _get_jira_routing()
    routing = extract_jira_routing(payload)
    result = {}
    if routing.issue_key:
        result["ticket_key"] = routing.issue_key
    if routing.project_key:
        result["project_key"] = routing.project_key
    if routing.comment_id:
        result["comment_id"] = routing.comment_id
    if routing.user_name:
        result["user_name"] = routing.user_name
    return result


def extract_slack_metadata(payload: dict) -> dict:
    extract_slack_routing = _get_slack_routing()
    routing = extract_slack_routing(payload)
    result = {}
    if routing.channel_id:
        result["channel_id"] = routing.channel_id
    if routing.team_id:
        result["team_id"] = routing.team_id
    if routing.user_id:
        result["user_id"] = routing.user_id
    if routing.thread_ts:
        result["thread_ts"] = routing.thread_ts
    return result


def extract_routing_metadata(webhook_source: str, payload: dict) -> dict:
    extractors = {
        "github": extract_github_metadata,
        "jira": extract_jira_metadata,
        "slack": extract_slack_metadata,
    }

    extractor = extractors.get(webhook_source)
    if not extractor:
        return {}

    return extractor(payload)


def extract_routing_metadata_typed(webhook_source: str, payload: dict) -> Optional[Union["GitHubRoutingMetadata", "JiraRoutingMetadata", "SlackRoutingMetadata"]]:
    extractors = {
        "github": _get_github_routing(),
        "jira": _get_jira_routing(),
        "slack": _get_slack_routing(),
    }

    extractor = extractors.get(webhook_source)
    if not extractor:
        return None

    return extractor(payload)


def build_source_metadata(webhook_source: str, payload: dict, **extra) -> dict:
    routing = extract_routing_metadata(webhook_source, payload)

    return {
        "webhook_source": webhook_source,
        "routing": routing,
        **extra,
        "payload": payload,
    }
