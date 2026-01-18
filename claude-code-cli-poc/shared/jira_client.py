"""
Jira API Client
===============
Wrapper for Jira API operations.
"""

import structlog
from jira import JIRA

from shared.config import get_settings

logger = structlog.get_logger(__name__)


class JiraClient:
    """Jira API Client."""

    def __init__(self):
        settings = get_settings()
        self.client = JIRA(
            server=settings.jira.base_url,
            basic_auth=(settings.jira.email, settings.jira.api_token),
        )
        self.ai_label = settings.jira.ai_label

    def get_ticket(self, ticket_id: str) -> dict:
        """Fetch ticket details from Jira."""
        issue = self.client.issue(ticket_id)

        # Extract error logs from attachments or description
        error_logs = ""
        for attachment in issue.fields.attachment:
            if "sentry" in attachment.filename.lower() or "error" in attachment.filename.lower():
                error_logs += f"\n--- {attachment.filename} ---\n"
                try:
                    error_logs += attachment.get().decode("utf-8")
                except Exception:
                    pass

        description = issue.fields.description or ""
        if "```" in description:
            error_logs += f"\n--- From Description ---\n{description}"

        return {
            "key": issue.key,
            "summary": issue.fields.summary,
            "description": description,
            "status": issue.fields.status.name,
            "priority": issue.fields.priority.name if issue.fields.priority else "Medium",
            "labels": issue.fields.labels,
            "error_logs": error_logs or "No error logs found",
            "reporter": issue.fields.reporter.displayName if issue.fields.reporter else "Unknown",
        }

    def update_status(self, ticket_id: str, status: str) -> bool:
        """Update ticket status."""
        issue = self.client.issue(ticket_id)
        transitions = self.client.transitions(issue)

        for t in transitions:
            if t["name"].lower() == status.lower():
                self.client.transition_issue(issue, t["id"])
                logger.info("Updated ticket status", ticket_id=ticket_id, status=status)
                return True

        logger.warning("Could not find transition", ticket_id=ticket_id, target_status=status)
        return False

    def add_comment(self, ticket_id: str, comment: str):
        """Add a comment to the ticket."""
        self.client.add_comment(ticket_id, comment)
        logger.info("Added comment to ticket", ticket_id=ticket_id)

    def has_ai_label(self, ticket: dict) -> bool:
        """Check if ticket has the AI processing label."""
        return self.ai_label in ticket.get("labels", [])
