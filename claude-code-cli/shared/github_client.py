"""GitHub utilities for webhook handling.

Provides:
- Webhook signature validation (security)
- URL parsing utilities
- Comment posting for bot responses

Note: Major GitHub operations (PR creation, file updates) are handled
by Claude Code via MCP tools.
"""

import hmac
import hashlib
import logging
from typing import Optional

import httpx

from shared.config import settings

logger = logging.getLogger("github_client")


def validate_webhook_signature(payload: bytes, signature: str) -> bool:
    """Validate GitHub webhook signature.

    Args:
        payload: Raw webhook payload bytes
        signature: X-Hub-Signature-256 header value

    Returns:
        True if signature is valid or no secret configured
    """
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True  # No secret configured, skip validation

    expected = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


def get_pr_number_from_url(url: str) -> Optional[int]:
    """Extract PR number from GitHub URL.

    Args:
        url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

    Returns:
        PR number or None if not found
    """
    try:
        parts = url.rstrip("/").split("/")
        if "pull" in parts:
            return int(parts[parts.index("pull") + 1])
    except (ValueError, IndexError):
        pass
    return None


def get_repo_from_url(url: str) -> Optional[str]:
    """Extract repository name from GitHub URL.

    Args:
        url: GitHub URL (PR, issue, or repo)

    Returns:
        Repository name (owner/repo) or None if not found
    """
    try:
        parts = url.split("/")
        owner_idx = parts.index("github.com") + 1
        return f"{parts[owner_idx]}/{parts[owner_idx + 1]}"
    except (ValueError, IndexError):
        return None


class GitHubClient:
    """GitHub API client for bot interactions."""

    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client.

        Args:
            token: GitHub token (uses settings if not provided)
        """
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        } if self.token else {}

    async def post_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str
    ) -> Optional[int]:
        """Post a comment on an issue or PR.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue or PR number
            body: Comment body (markdown)

        Returns:
            Comment ID or None if failed
        """
        if not self.token:
            logger.warning(f"GitHub not configured, would comment on {owner}/{repo}#{issue_number}")
            return None

        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={"body": body},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Posted comment on {owner}/{repo}#{issue_number}")
                return data.get("id")
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to post comment: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Failed to post comment: {e}")
            return None

    async def add_reaction(
        self,
        owner: str,
        repo: str,
        comment_id: int,
        reaction: str
    ) -> bool:
        """Add a reaction to a comment.

        Args:
            owner: Repository owner
            repo: Repository name
            comment_id: Comment ID
            reaction: Reaction name (+1, -1, laugh, confused, heart, hooray, rocket, eyes)

        Returns:
            True if successful
        """
        if not self.token:
            logger.warning(f"GitHub not configured, would add {reaction} to comment")
            return False

        url = f"{self.base_url}/repos/{owner}/{repo}/issues/comments/{comment_id}/reactions"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={**self.headers, "Accept": "application/vnd.github+json"},
                    json={"content": reaction},
                    timeout=30.0
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to add reaction: {e}")
            return False

    async def post_comment_from_url(
        self,
        pr_url: str,
        body: str
    ) -> Optional[int]:
        """Post a comment using PR URL.

        Args:
            pr_url: Full PR URL
            body: Comment body

        Returns:
            Comment ID or None
        """
        repo = get_repo_from_url(pr_url)
        pr_number = get_pr_number_from_url(pr_url)

        if not repo or not pr_number:
            logger.error(f"Could not parse PR URL: {pr_url}")
            return None

        owner, repo_name = repo.split("/")
        return await self.post_comment(owner, repo_name, pr_number, body)
