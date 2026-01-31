from typing import Any
import structlog

logger = structlog.get_logger(__name__)

SUPPORTED_EVENTS = {
    "issues": ["opened", "edited", "labeled"],
    "issue_comment": ["created"],
    "pull_request": ["opened", "synchronize", "reopened"],
    "pull_request_review_comment": ["created"],
    "push": None,
}


def should_process_event(event_type: str, action: str | None) -> bool:
    if event_type not in SUPPORTED_EVENTS:
        return False

    allowed_actions = SUPPORTED_EVENTS[event_type]
    if allowed_actions is None:
        return True

    return action in allowed_actions


def extract_task_info(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    task_info: dict[str, Any] = {
        "source": "github",
        "event_type": event_type,
        "action": payload.get("action"),
    }

    if "repository" in payload:
        repo = payload["repository"]
        task_info["repository"] = {
            "full_name": repo.get("full_name"),
            "clone_url": repo.get("clone_url"),
            "default_branch": repo.get("default_branch"),
        }

    if event_type in ("issues", "issue_comment"):
        issue = payload.get("issue", {})
        task_info["issue"] = {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "body": issue.get("body"),
            "labels": [label.get("name") for label in issue.get("labels", [])],
        }
        if event_type == "issue_comment":
            comment = payload.get("comment", {})
            task_info["comment"] = {
                "id": comment.get("id"),
                "body": comment.get("body"),
                "user": comment.get("user", {}).get("login"),
            }

    elif event_type in ("pull_request", "pull_request_review_comment"):
        pr = payload.get("pull_request", {})
        task_info["pull_request"] = {
            "number": pr.get("number"),
            "title": pr.get("title"),
            "body": pr.get("body"),
            "head_ref": pr.get("head", {}).get("ref"),
            "base_ref": pr.get("base", {}).get("ref"),
        }
        if event_type == "pull_request_review_comment":
            comment = payload.get("comment", {})
            task_info["comment"] = {
                "id": comment.get("id"),
                "body": comment.get("body"),
                "path": comment.get("path"),
                "line": comment.get("line"),
            }

    elif event_type == "push":
        task_info["push"] = {
            "ref": payload.get("ref"),
            "before": payload.get("before"),
            "after": payload.get("after"),
            "commits": [
                {"message": c.get("message"), "sha": c.get("id")}
                for c in payload.get("commits", [])
            ],
        }

    return task_info
