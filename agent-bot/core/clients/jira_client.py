import structlog
from typing import Any

logger = structlog.get_logger()


class JiraMCPClient:
    def __init__(self, mcp_client: Any) -> None:
        self._client = mcp_client

    async def create_comment(
        self,
        issue_key: str,
        body: str,
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="jira_add_comment",
                arguments={
                    "issue_key": issue_key,
                    "comment": body,
                },
            )

            logger.info(
                "jira_comment_created",
                issue_key=issue_key,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "jira_comment_failed",
                issue_key=issue_key,
                error=str(e),
            )
            return False

    async def update_issue(
        self,
        issue_key: str,
        fields: dict[str, Any],
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="jira_update_issue",
                arguments={
                    "issue_key": issue_key,
                    "fields": fields,
                },
            )

            logger.info(
                "jira_issue_updated",
                issue_key=issue_key,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "jira_issue_update_failed",
                issue_key=issue_key,
                error=str(e),
            )
            return False

    async def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="jira_transition_issue",
                arguments={
                    "issue_key": issue_key,
                    "transition_id": transition_id,
                },
            )

            logger.info(
                "jira_issue_transitioned",
                issue_key=issue_key,
                transition_id=transition_id,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "jira_transition_failed",
                issue_key=issue_key,
                transition_id=transition_id,
                error=str(e),
            )
            return False

    async def assign_issue(
        self,
        issue_key: str,
        assignee: str,
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="jira_assign_issue",
                arguments={
                    "issue_key": issue_key,
                    "assignee": assignee,
                },
            )

            logger.info(
                "jira_issue_assigned",
                issue_key=issue_key,
                assignee=assignee,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "jira_assign_failed",
                issue_key=issue_key,
                assignee=assignee,
                error=str(e),
            )
            return False

    async def add_label(
        self,
        issue_key: str,
        label: str,
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="jira_add_label",
                arguments={
                    "issue_key": issue_key,
                    "label": label,
                },
            )

            logger.info(
                "jira_label_added",
                issue_key=issue_key,
                label=label,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "jira_label_failed",
                issue_key=issue_key,
                label=label,
                error=str(e),
            )
            return False
