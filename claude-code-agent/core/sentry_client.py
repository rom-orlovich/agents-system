"""Sentry API client for error tracking and monitoring."""

import os
import httpx
import structlog
from typing import Optional, Dict, Any, List

logger = structlog.get_logger()


class SentryClient:
    """Client for interacting with Sentry API."""

    def __init__(
        self,
        auth_token: Optional[str] = None,
        org_slug: Optional[str] = None
    ):
        """Initialize Sentry client with auth token and org slug."""
        self.auth_token = auth_token or os.getenv("SENTRY_AUTH_TOKEN")
        self.org_slug = org_slug or os.getenv("SENTRY_ORG_SLUG")
        self.base_url = "https://sentry.io/api/0"

        self.headers = {
            "Content-Type": "application/json"
        }

        if self.auth_token:
            self.headers["Authorization"] = f"Bearer {self.auth_token}"
        else:
            logger.warning("sentry_client_no_token", message="SENTRY_AUTH_TOKEN not configured")

    def _check_config(self) -> None:
        """Check if client is properly configured."""
        if not self.auth_token:
            raise ValueError("Sentry client not properly configured. Check SENTRY_AUTH_TOKEN")
        if not self.org_slug:
            raise ValueError("Sentry org slug not configured. Check SENTRY_ORG_SLUG")

    async def get_issue(
        self,
        issue_id: str
    ) -> Dict[str, Any]:
        """
        Get issue details from Sentry.

        Args:
            issue_id: Sentry issue ID

        Returns:
            Issue data dict
        """
        self._check_config()

        url = f"{self.base_url}/organizations/{self.org_slug}/issues/{issue_id}/"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("sentry_issue_fetched", issue_id=issue_id)
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "sentry_get_issue_failed",
                issue_id=issue_id,
                status_code=e.response.status_code,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "sentry_api_error",
                issue_id=issue_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def get_event(
        self,
        project_slug: str,
        event_id: str
    ) -> Dict[str, Any]:
        """
        Get event details from Sentry.

        Args:
            project_slug: Project slug
            event_id: Event ID

        Returns:
            Event data dict
        """
        self._check_config()

        url = f"{self.base_url}/projects/{self.org_slug}/{project_slug}/events/{event_id}/"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("sentry_event_fetched", project=project_slug, event_id=event_id)
                return response.json()

        except Exception as e:
            logger.error("sentry_get_event_failed", project=project_slug, event_id=event_id, error=str(e))
            raise

    async def update_issue(
        self,
        issue_id: str,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        is_bookmarked: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update Sentry issue.

        Args:
            issue_id: Sentry issue ID
            status: Issue status ("resolved", "ignored", "unresolved")
            assigned_to: User ID to assign to
            is_bookmarked: Bookmark status

        Returns:
            Updated issue data
        """
        self._check_config()

        url = f"{self.base_url}/organizations/{self.org_slug}/issues/{issue_id}/"

        payload: Dict[str, Any] = {}

        if status:
            payload["status"] = status

        if assigned_to is not None:
            payload["assignedTo"] = assigned_to

        if is_bookmarked is not None:
            payload["isBookmarked"] = is_bookmarked

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("sentry_issue_updated", issue_id=issue_id, updates=list(payload.keys()))
                return response.json()

        except Exception as e:
            logger.error("sentry_update_issue_failed", issue_id=issue_id, error=str(e))
            raise

    async def add_comment(
        self,
        issue_id: str,
        comment_text: str
    ) -> Dict[str, Any]:
        """
        Add a comment to a Sentry issue.

        Args:
            issue_id: Sentry issue ID
            comment_text: Comment text

        Returns:
            API response dict
        """
        self._check_config()

        url = f"{self.base_url}/organizations/{self.org_slug}/issues/{issue_id}/notes/"

        payload = {
            "text": comment_text
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("sentry_comment_added", issue_id=issue_id)
                return response.json()

        except Exception as e:
            logger.error("sentry_add_comment_failed", issue_id=issue_id, error=str(e))
            raise

    async def get_stacktrace(
        self,
        project_slug: str,
        event_id: str
    ) -> Optional[str]:
        """
        Get formatted stacktrace from event.

        Args:
            project_slug: Project slug
            event_id: Event ID

        Returns:
            Formatted stacktrace string or None
        """
        try:
            event = await self.get_event(project_slug, event_id)

            # Extract stacktrace from event
            entries = event.get("entries", [])
            for entry in entries:
                if entry.get("type") == "exception":
                    values = entry.get("data", {}).get("values", [])
                    if values:
                        stacktrace = values[0].get("stacktrace", {})
                        frames = stacktrace.get("frames", [])

                        if frames:
                            # Format stacktrace
                            lines = []
                            for frame in reversed(frames):  # Reverse to show most recent first
                                filename = frame.get("filename", "unknown")
                                function = frame.get("function", "unknown")
                                lineno = frame.get("lineNo", "?")
                                context = frame.get("context", [])

                                lines.append(f"  File \"{filename}\", line {lineno}, in {function}")

                                if context:
                                    for ctx_line in context:
                                        lines.append(f"    {ctx_line[1]}")

                            return "\n".join(lines)

            return None

        except Exception as e:
            logger.error("sentry_get_stacktrace_failed", project=project_slug, event_id=event_id, error=str(e))
            return None

    async def resolve_issue(
        self,
        issue_id: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve a Sentry issue.

        Args:
            issue_id: Sentry issue ID
            comment: Optional resolution comment

        Returns:
            Updated issue data
        """
        if comment:
            await self.add_comment(issue_id, comment)

        return await self.update_issue(issue_id, status="resolved")


# Global client instance
sentry_client = SentryClient()
