"""Slack domain routing metadata extractor."""

from api.webhooks.slack.models import SlackRoutingMetadata


def extract_slack_routing(payload: dict) -> SlackRoutingMetadata:
    channel_id = ""
    team_id = ""
    user_id = None
    user_name = None
    thread_ts = None

    event = payload.get("event", {})
    if event:
        if event.get("channel"):
            channel_id = event["channel"]

        if event.get("thread_ts"):
            thread_ts = event["thread_ts"]
        elif event.get("ts"):
            thread_ts = event["ts"]

        if event.get("user"):
            user_id = event["user"]

    if payload.get("channel_id"):
        channel_id = payload["channel_id"]

    if payload.get("user_id"):
        user_id = payload["user_id"]

    if payload.get("team_id"):
        team_id = payload["team_id"]

    if payload.get("user_name"):
        user_name = payload["user_name"]

    return SlackRoutingMetadata(
        channel_id=channel_id,
        team_id=team_id,
        user_id=user_id,
        user_name=user_name,
        thread_ts=thread_ts,
    )
