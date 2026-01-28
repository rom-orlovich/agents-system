import json
from typing import Any, Dict, List, Optional

from domain.models.notifications import TaskNotification, TaskSummary
from domain.models.routing import RoutingMetadata


class NotificationBuilder:

    @staticmethod
    def build_blocks(notification: TaskNotification) -> List[Dict[str, Any]]:
        blocks = []

        status_emoji = notification.get_status_emoji()
        status_text = notification.get_status_text()

        header_text = (
            f"{status_emoji} *Task {status_text}*\n"
            f"*Source:* {notification.source.value.title()}\n"
            f"*Command:* {notification.command}\n"
            f"*Task ID:* `{notification.task_id}`"
        )

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": header_text,
            }
        })

        if notification.success and notification.result:
            result_preview = (
                notification.result[:500] + "..."
                if len(notification.result) > 500
                else notification.result
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Result:*\n```{result_preview}```",
                }
            })

        if notification.error:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error:*\n```{notification.error}```",
                }
            })

        if notification.cost_usd > 0:
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f"💰 Cost: ${notification.cost_usd:.4f}",
                }]
            })

        if notification.pr_url:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔗 <{notification.pr_url}|View Pull Request>",
                }
            })

        if notification.ticket_key:
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f"🎫 Jira: `{notification.ticket_key}`",
                }]
            })

        return blocks

    @staticmethod
    def build_approval_buttons(
        task_id: str,
        command: str,
        routing: Optional[RoutingMetadata],
        source: str,
    ) -> List[Dict[str, Any]]:
        value_data = {
            "original_task_id": task_id,
            "command": command,
            "source": source,
        }

        if routing:
            value_data["routing"] = routing.to_dict() if hasattr(routing, "to_dict") else routing

        buttons = []

        buttons.append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "✅ Approve",
                "emoji": True,
            },
            "style": "primary",
            "action_id": "approve_task",
            "value": json.dumps({**value_data, "action": "approve"}),
        })

        buttons.append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "👀 Review",
                "emoji": True,
            },
            "action_id": "review_task",
            "value": json.dumps({**value_data, "action": "review"}),
        })

        buttons.append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "❌ Reject",
                "emoji": True,
            },
            "style": "danger",
            "action_id": "reject_task",
            "value": json.dumps({**value_data, "action": "reject"}),
        })

        return [{
            "type": "actions",
            "elements": buttons,
        }]

    @staticmethod
    def build_task_completion_blocks(
        summary: TaskSummary,
        routing: Optional[Dict[str, Any]],
        requires_approval: bool,
        task_id: str,
        cost_usd: float,
        command: str,
        source: str,
    ) -> List[Dict[str, Any]]:
        blocks = []

        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 Task Complete: {command}",
                "emoji": True,
            }
        })

        summary_text = f"*Summary:* {summary.summary}"
        if summary.classification and summary.classification != "SIMPLE":
            summary_text += f"\n*Classification:* {summary.classification}"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": summary_text,
            }
        })

        if summary.what_was_done:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*What was done:* {summary.what_was_done}",
                }
            })

        if summary.key_insights:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Key insights:* {summary.key_insights}",
                }
            })

        context_elements = [
            {"type": "mrkdwn", "text": f"*Source:* {source.title()}"},
            {"type": "mrkdwn", "text": f"*Task ID:* `{task_id}`"},
        ]
        if cost_usd > 0:
            context_elements.append(
                {"type": "mrkdwn", "text": f"💰 ${cost_usd:.4f}"}
            )

        blocks.append({
            "type": "context",
            "elements": context_elements,
        })

        if routing:
            routing_parts = []
            if routing.get("repo"):
                routing_parts.append(f"*Repo:* {routing['repo']}")
            if routing.get("pr_number"):
                routing_parts.append(f"*PR:* #{routing['pr_number']}")
            if routing.get("ticket_key"):
                routing_parts.append(f"*Ticket:* {routing['ticket_key']}")

            if routing_parts:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": " | ".join(routing_parts)}
                    ],
                })

        if requires_approval:
            routing_metadata = None
            if routing:
                routing_metadata = RoutingMetadata(
                    repo=routing.get("repo"),
                    pr_number=routing.get("pr_number"),
                    ticket_key=routing.get("ticket_key"),
                )

            approval_blocks = NotificationBuilder.build_approval_buttons(
                task_id=task_id,
                command=command,
                routing=routing_metadata,
                source=source,
            )
            blocks.extend(approval_blocks)

        return blocks
