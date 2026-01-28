"""GitHub domain response handler."""

import os
import json
import subprocess
from typing import Optional
import structlog

from api.webhooks.github.models import GitHubRoutingMetadata
from api.webhooks.github.errors import GitHubResponseError, GitHubErrorContext
from api.webhooks.github.validation import validate_response_format

logger = structlog.get_logger()

try:
    from core.github_client import github_client
except ImportError:
    github_client = None


class GitHubResponseHandler:
    async def post_response(self, routing: GitHubRoutingMetadata, result: str) -> tuple[bool, Optional[dict]]:
        if not routing.owner or not routing.repo:
            logger.error("github_routing_missing", routing=routing.model_dump())
            return False, None

        if not routing.pr_number and not routing.issue_number:
            logger.error("github_no_pr_or_issue", routing=routing.model_dump())
            return False, None

        try:
            if routing.pr_number:
                return await self._post_to_pr(routing, result)
            else:
                return await self._post_to_issue(routing, result)
        except GitHubResponseError:
            raise
        except Exception as e:
            context = GitHubErrorContext(
                repo=f"{routing.owner}/{routing.repo}",
                issue_number=routing.issue_number,
                pr_number=routing.pr_number
            )
            raise GitHubResponseError(f"Failed to post response: {str(e)}", context=context)

    async def _post_to_pr(self, routing: GitHubRoutingMetadata, result: str) -> tuple[bool, Optional[dict]]:
        is_valid, error_msg = validate_response_format(result, "pr_review")
        if not is_valid:
            logger.warning(
                "github_pr_response_format_invalid",
                error=error_msg,
                pr_number=routing.pr_number
            )

        if github_client is None:
            success = await self._post_with_curl(
                routing.owner, routing.repo, routing.pr_number, result
            )
            return success, None

        response = await github_client.post_pr_comment(
            routing.owner, routing.repo, routing.pr_number, result
        )
        logger.info("github_response_posted", type="pr", number=routing.pr_number)
        return True, response

    async def _post_to_issue(self, routing: GitHubRoutingMetadata, result: str) -> tuple[bool, Optional[dict]]:
        is_valid, error_msg = validate_response_format(result, "issue_analysis")
        if not is_valid:
            logger.warning(
                "github_issue_response_format_invalid",
                error=error_msg,
                issue_number=routing.issue_number
            )

        if github_client is None:
            success = await self._post_with_curl(
                routing.owner, routing.repo, routing.issue_number, result
            )
            return success, None

        response = await github_client.post_issue_comment(
            routing.owner, routing.repo, routing.issue_number, result
        )
        logger.info("github_response_posted", type="issue", number=routing.issue_number)
        return True, response

    async def _post_with_curl(
        self, owner: str, repo: str, number: int, body: str
    ) -> bool:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            logger.error("github_token_missing")
            return False

        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"

        try:
            proc = subprocess.run(
                [
                    "curl", "-s", "-X", "POST", url,
                    "-H", f"Authorization: Bearer {token}",
                    "-H", "Accept: application/vnd.github+json",
                    "-d", json.dumps({"body": body})
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            return proc.returncode == 0
        except Exception as e:
            logger.error("github_curl_failed", error=str(e))
            return False


github_response_handler = GitHubResponseHandler()
