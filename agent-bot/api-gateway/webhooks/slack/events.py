from typing import Any
import structlog

logger = structlog.get_logger(__name__)

SUPPORTED_EVENT_TYPES = ["message", "app_mention"]


def should_process_event(event: dict[str, Any], bot_user_id: str | None = None) -> bool:
    event_type = event.get("type")
    if event_type not in SUPPORTED_EVENT_TYPES:
        return False

    if event.get("subtype") == "bot_message":
        return False

    if bot_user_id and event.get("user") == bot_user_id:
        return False

    if event_type == "message" and "thread_ts" not in event:
        text = event.get("text", "")
        if "@agent" not in text.lower() and "<@" not in text:
            return False

    return True


def extract_task_info(event: dict[str, Any], team_id: str) -> dict[str, Any]:
    task_info: dict[str, Any] = {
        "source": "slack",
        "event_type": event.get("type"),
        "team_id": team_id,
        "channel": event.get("channel"),
        "user": event.get("user"),
        "text": event.get("text"),
        "ts": event.get("ts"),
    }

    if "thread_ts" in event:
        task_info["thread_ts"] = event["thread_ts"]
    else:
        task_info["thread_ts"] = event.get("ts")

    if "files" in event:
        task_info["files"] = [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "filetype": f.get("filetype"),
                "url_private": f.get("url_private"),
            }
            for f in event["files"]
        ]

    return task_info
