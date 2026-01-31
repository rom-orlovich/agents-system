from typing import Any
import structlog

logger = structlog.get_logger(__name__)

SUPPORTED_EVENTS = [
    "jira:issue_created",
    "jira:issue_updated",
    "comment_created",
]

AI_FIX_LABEL = "AI-Fix"


def should_process_event(webhook_event: str, issue_data: dict[str, Any]) -> bool:
    if webhook_event not in SUPPORTED_EVENTS:
        return False

    labels = issue_data.get("fields", {}).get("labels", [])
    return AI_FIX_LABEL in labels


def extract_task_info(webhook_event: str, payload: dict[str, Any]) -> dict[str, Any]:
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})

    task_info: dict[str, Any] = {
        "source": "jira",
        "event_type": webhook_event,
        "issue": {
            "key": issue.get("key"),
            "id": issue.get("id"),
            "summary": fields.get("summary"),
            "description": fields.get("description"),
            "issue_type": fields.get("issuetype", {}).get("name"),
            "status": fields.get("status", {}).get("name"),
            "priority": fields.get("priority", {}).get("name"),
            "labels": fields.get("labels", []),
            "project": {
                "key": fields.get("project", {}).get("key"),
                "name": fields.get("project", {}).get("name"),
            },
        },
    }

    if webhook_event == "comment_created":
        comment = payload.get("comment", {})
        task_info["comment"] = {
            "id": comment.get("id"),
            "body": comment.get("body"),
            "author": comment.get("author", {}).get("displayName"),
        }

    custom_fields = {}
    for key, value in fields.items():
        if key.startswith("customfield_"):
            custom_fields[key] = value
    if custom_fields:
        task_info["custom_fields"] = custom_fields

    return task_info
