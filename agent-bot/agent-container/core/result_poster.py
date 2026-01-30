import structlog
from typing import Dict, Any
from enum import Enum


logger = structlog.get_logger()


class WebhookProvider(str, Enum):
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    SENTRY = "sentry"


class ResultPoster:
    def __init__(self, mcp_client: Any):
        self.mcp_client = mcp_client

    async def post_result(
        self, provider: WebhookProvider, metadata: Dict[str, Any], result: str
    ) -> bool:
        try:
            if provider == WebhookProvider.GITHUB:
                return await self._post_github_result(metadata, result)
            elif provider == WebhookProvider.JIRA:
                return await self._post_jira_result(metadata, result)
            elif provider == WebhookProvider.SLACK:
                return await self._post_slack_result(metadata, result)
            elif provider == WebhookProvider.SENTRY:
                return await self._post_sentry_result(metadata, result)
            else:
                logger.warning("unknown_provider", provider=provider)
                return False
        except Exception as e:
            logger.error("result_posting_failed", provider=provider, error=str(e))
            return False

    async def _post_github_result(
        self, metadata: Dict[str, Any], result: str
    ) -> bool:
        repo_full_name = metadata.get("repository", "")
        if not repo_full_name or "/" not in repo_full_name:
            logger.error("invalid_github_metadata", metadata=metadata)
            return False

        owner, repo = repo_full_name.split("/", 1)
        action = metadata.get("action", "")

        if "pull_request" in action or "pr" in action.lower():
            pr_number = metadata.get("pr_number") or metadata.get("number")
            if not pr_number:
                logger.error("missing_pr_number", metadata=metadata)
                return False

            success = await self.mcp_client.call_tool(
                name="github_post_pr_comment",
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "pr_number": int(pr_number),
                    "comment": f"## Agent Result\n\n{result}",
                },
            )

            if success:
                await self.mcp_client.call_tool(
                    name="github_add_pr_reaction",
                    arguments={
                        "owner": owner,
                        "repo": repo,
                        "pr_number": int(pr_number),
                        "reaction": "rocket",
                    },
                )

            return success

        elif "issue" in action:
            issue_number = metadata.get("issue_number") or metadata.get("number")
            if not issue_number:
                logger.error("missing_issue_number", metadata=metadata)
                return False

            return await self.mcp_client.call_tool(
                name="github_post_issue_comment",
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "issue_number": int(issue_number),
                    "comment": f"## Agent Result\n\n{result}",
                },
            )

        logger.warning("unsupported_github_action", action=action)
        return False

    async def _post_jira_result(self, metadata: Dict[str, Any], result: str) -> bool:
        issue_key = metadata.get("issue_key")
        if not issue_key:
            logger.error("missing_jira_issue_key", metadata=metadata)
            return False

        return await self.mcp_client.call_tool(
            name="jira_add_comment",
            arguments={"issue_key": issue_key, "comment": result},
        )

    async def _post_slack_result(self, metadata: Dict[str, Any], result: str) -> bool:
        channel = metadata.get("channel")
        thread_ts = metadata.get("thread_ts")

        if not channel:
            logger.error("missing_slack_channel", metadata=metadata)
            return False

        return await self.mcp_client.call_tool(
            name="slack_post_message",
            arguments={"channel": channel, "text": result, "thread_ts": thread_ts},
        )

    async def _post_sentry_result(
        self, metadata: Dict[str, Any], result: str
    ) -> bool:
        issue_id = metadata.get("issue_id")
        if not issue_id:
            logger.error("missing_sentry_issue_id", metadata=metadata)
            return False

        return await self.mcp_client.call_tool(
            name="sentry_add_comment",
            arguments={"issue_id": issue_id, "comment": result},
        )
