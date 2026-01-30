import structlog
from typing import Any

logger = structlog.get_logger()


class GitHubMCPClient:
    def __init__(self, mcp_client: Any) -> None:
        self._client = mcp_client

    async def create_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="github_post_issue_comment",
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "issue_number": issue_number,
                    "comment": body,
                },
            )

            logger.info(
                "github_comment_created",
                owner=owner,
                repo=repo,
                issue_number=issue_number,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "github_comment_failed",
                owner=owner,
                repo=repo,
                issue_number=issue_number,
                error=str(e),
            )
            return False

    async def create_pr_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="github_post_pr_comment",
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "pr_number": pr_number,
                    "comment": body,
                },
            )

            logger.info(
                "github_pr_review_created",
                owner=owner,
                repo=repo,
                pr_number=pr_number,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "github_pr_review_failed",
                owner=owner,
                repo=repo,
                pr_number=pr_number,
                error=str(e),
            )
            return False

    async def add_reaction(
        self,
        owner: str,
        repo: str,
        comment_id: int,
        reaction: str,
    ) -> bool:
        try:
            result = await self._client.call_tool(
                name="github_add_reaction",
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "comment_id": comment_id,
                    "reaction": reaction,
                },
            )

            logger.info(
                "github_reaction_added",
                owner=owner,
                repo=repo,
                comment_id=comment_id,
                reaction=reaction,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "github_reaction_failed",
                owner=owner,
                repo=repo,
                comment_id=comment_id,
                error=str(e),
            )
            return False

    async def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> bool:
        try:
            arguments: dict[str, Any] = {
                "owner": owner,
                "repo": repo,
                "issue_number": issue_number,
            }

            if title:
                arguments["title"] = title
            if body:
                arguments["body"] = body
            if state:
                arguments["state"] = state

            result = await self._client.call_tool(
                name="github_update_issue",
                arguments=arguments,
            )

            logger.info(
                "github_issue_updated",
                owner=owner,
                repo=repo,
                issue_number=issue_number,
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "github_issue_update_failed",
                owner=owner,
                repo=repo,
                issue_number=issue_number,
                error=str(e),
            )
            return False
