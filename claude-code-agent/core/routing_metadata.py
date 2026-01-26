"""
Routing metadata extractors for webhook response posting.

Each extractor takes a raw webhook payload and returns clean,
flat metadata that the brain agent can use for response routing.
"""

from typing import Optional


def extract_github_metadata(payload: dict) -> dict:
    """
    Extract GitHub routing metadata from webhook payload.

    Returns:
        {
            "owner": "org-name",
            "repo": "repo-name",
            "issue_number": 123,      # if issue event
            "pr_number": 456,         # if PR event
            "comment_id": 789,        # if comment event
        }
    """
    metadata = {}

    # Repository info
    repo = payload.get("repository", {})
    full_name = repo.get("full_name", "")
    if "/" in full_name:
        owner, repo_name = full_name.split("/", 1)
        metadata["owner"] = owner
        metadata["repo"] = repo_name

    # Issue info
    issue = payload.get("issue", {})
    if issue.get("number"):
        metadata["issue_number"] = issue["number"]

    # PR info (can be in issue or pull_request)
    pr = payload.get("pull_request", {})
    if pr.get("number"):
        metadata["pr_number"] = pr["number"]
    elif issue.get("pull_request"):
        # Issue is actually a PR
        metadata["pr_number"] = issue["number"]

    # Comment info
    comment = payload.get("comment", {})
    if comment.get("id"):
        metadata["comment_id"] = comment["id"]

    # Sender info
    sender = payload.get("sender", {})
    if sender.get("login"):
        metadata["sender"] = sender["login"]

    return metadata


def extract_jira_metadata(payload: dict) -> dict:
    """
    Extract Jira routing metadata from webhook payload.

    Returns:
        {
            "ticket_key": "PROJ-123",
            "project_key": "PROJ",
            "issue_id": "10001",
        }
    """
    metadata = {}

    # Issue info - handle both formats
    issue = payload.get("issue", {})

    # Key (e.g., PROJ-123)
    if issue.get("key"):
        metadata["ticket_key"] = issue["key"]
        # Extract project from key
        if "-" in issue["key"]:
            metadata["project_key"] = issue["key"].split("-")[0]

    # Issue ID
    if issue.get("id"):
        metadata["issue_id"] = str(issue["id"])

    # Project info from fields
    fields = issue.get("fields", {})
    project = fields.get("project", {})
    if project.get("key"):
        metadata["project_key"] = project["key"]

    # Comment info (for comment events)
    comment = payload.get("comment", {})
    if comment.get("id"):
        metadata["comment_id"] = str(comment["id"])

    # User info
    user = payload.get("user", {})
    if user.get("accountId"):
        metadata["user_id"] = user["accountId"]
    elif user.get("name"):
        metadata["user_name"] = user["name"]

    return metadata


def extract_slack_metadata(payload: dict) -> dict:
    """
    Extract Slack routing metadata from webhook payload.

    Returns:
        {
            "channel_id": "C123456",
            "thread_ts": "1234567890.123456",
            "user_id": "U123456",
            "message_ts": "1234567890.123456",
        }
    """
    metadata = {}

    # Event-based payload (Events API)
    event = payload.get("event", {})
    if event:
        if event.get("channel"):
            metadata["channel_id"] = event["channel"]

        # Thread timestamp - prefer thread_ts, fallback to ts
        if event.get("thread_ts"):
            metadata["thread_ts"] = event["thread_ts"]
        elif event.get("ts"):
            # If no thread_ts, use message ts (will create new thread)
            metadata["thread_ts"] = event["ts"]
            metadata["message_ts"] = event["ts"]

        if event.get("user"):
            metadata["user_id"] = event["user"]

    # Slash command payload
    if payload.get("channel_id"):
        metadata["channel_id"] = payload["channel_id"]
    if payload.get("user_id"):
        metadata["user_id"] = payload["user_id"]

    # Response URL (for slash commands)
    if payload.get("response_url"):
        metadata["response_url"] = payload["response_url"]

    return metadata


def extract_routing_metadata(webhook_source: str, payload: dict) -> dict:
    """
    Main dispatcher - extracts routing metadata based on source.

    Args:
        webhook_source: "github", "jira", or "slack"
        payload: Raw webhook payload

    Returns:
        Clean routing metadata dict
    """
    extractors = {
        "github": extract_github_metadata,
        "jira": extract_jira_metadata,
        "slack": extract_slack_metadata,
    }

    extractor = extractors.get(webhook_source)
    if not extractor:
        return {}

    return extractor(payload)


def build_source_metadata(webhook_source: str, payload: dict, **extra) -> dict:
    """
    Build complete source_metadata for task creation.

    Combines routing metadata with any extra fields.

    Args:
        webhook_source: "github", "jira", or "slack"
        payload: Raw webhook payload
        **extra: Additional fields (command, webhook_name, etc.)

    Returns:
        Complete source_metadata dict ready for JSON serialization
    """
    routing = extract_routing_metadata(webhook_source, payload)

    return {
        "webhook_source": webhook_source,
        "routing": routing,  # Clean, flat routing info
        **extra,
        "payload": payload,  # Keep original for reference
    }
