"""GitHub utilities for webhook handling.

Note: All GitHub operations (PR creation, file updates, comments) are handled
by Claude Code via MCP tools. This module only provides:
- Webhook signature validation (security)
- URL parsing utilities
"""

import hmac
import hashlib
from typing import Optional

from config import settings


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
