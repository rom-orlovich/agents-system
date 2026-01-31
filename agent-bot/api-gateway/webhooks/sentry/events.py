from typing import Any
import structlog

logger = structlog.get_logger(__name__)

SUPPORTED_ACTIONS = ["created", "resolved", "assigned", "ignored"]


def should_process_event(action: str, data: dict[str, Any]) -> bool:
    if action not in SUPPORTED_ACTIONS:
        return False

    if action == "created":
        return True

    return False


def extract_task_info(action: str, data: dict[str, Any]) -> dict[str, Any]:
    issue = data.get("data", {}).get("issue", {})

    task_info: dict[str, Any] = {
        "source": "sentry",
        "event_type": action,
        "issue": {
            "id": issue.get("id"),
            "title": issue.get("title"),
            "culprit": issue.get("culprit"),
            "level": issue.get("level"),
            "status": issue.get("status"),
            "first_seen": issue.get("firstSeen"),
            "last_seen": issue.get("lastSeen"),
            "count": issue.get("count"),
            "permalink": issue.get("permalink"),
        },
        "project": {
            "id": issue.get("project", {}).get("id"),
            "name": issue.get("project", {}).get("name"),
            "slug": issue.get("project", {}).get("slug"),
        },
    }

    metadata = issue.get("metadata", {})
    if metadata:
        task_info["metadata"] = {
            "type": metadata.get("type"),
            "value": metadata.get("value"),
            "filename": metadata.get("filename"),
            "function": metadata.get("function"),
        }

    tags = issue.get("tags", [])
    task_info["tags"] = {tag.get("key"): tag.get("value") for tag in tags}

    return task_info
