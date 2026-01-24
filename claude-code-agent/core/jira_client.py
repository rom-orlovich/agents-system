"""Jira API client for webhook interactions and workflow automation."""

import os
import base64
import httpx
import structlog
from typing import Optional, Dict, Any, List

logger = structlog.get_logger()


class JiraClient:
    """Client for interacting with Jira API."""

    def __init__(
        self,
        jira_url: Optional[str] = None,
        jira_email: Optional[str] = None,
        jira_api_token: Optional[str] = None
    ):
        """Initialize Jira client with credentials."""
        self.jira_url = (jira_url or os.getenv("JIRA_URL", "")).rstrip("/")
        self.jira_email = jira_email or os.getenv("JIRA_EMAIL")
        self.jira_api_token = jira_api_token or os.getenv("JIRA_API_TOKEN")

        if not all([self.jira_url, self.jira_email, self.jira_api_token]):
            logger.warning(
                "jira_client_incomplete_config",
                has_url=bool(self.jira_url),
                has_email=bool(self.jira_email),
                has_token=bool(self.jira_api_token)
            )

        # Create basic auth header
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if self.jira_email and self.jira_api_token:
            auth_string = f"{self.jira_email}:{self.jira_api_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            self.headers["Authorization"] = f"Basic {auth_b64}"

    def _check_config(self) -> None:
        """Check if client is properly configured."""
        if not all([self.jira_url, self.jira_email, self.jira_api_token]):
            raise ValueError("Jira client not properly configured. Check JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN")

    async def post_comment(
        self,
        issue_key: str,
        comment_text: str
    ) -> Dict[str, Any]:
        """
        Post a comment to a Jira issue.

        Args:
            issue_key: Jira issue key (e.g., "PROJ-123")
            comment_text: Comment text (plain text or Atlassian Document Format)

        Returns:
            API response dict
        """
        self._check_config()

        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}/comment"

        # Format comment in Atlassian Document Format
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment_text
                            }
                        ]
                    }
                ]
            }
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

                logger.info(
                    "jira_comment_posted",
                    issue_key=issue_key,
                    comment_id=response.json().get("id")
                )

                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "jira_comment_failed",
                issue_key=issue_key,
                status_code=e.response.status_code,
                error=str(e),
                response_text=e.response.text[:500] if e.response.text else None
            )
            raise
        except Exception as e:
            logger.error(
                "jira_api_error",
                issue_key=issue_key,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Get issue details from Jira.

        Args:
            issue_key: Jira issue key

        Returns:
            Issue data dict
        """
        self._check_config()

        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("jira_issue_fetched", issue_key=issue_key)
                return response.json()

        except Exception as e:
            logger.error("jira_get_issue_failed", issue_key=issue_key, error=str(e))
            raise

    async def update_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any]
    ) -> None:
        """
        Update Jira issue fields.

        Args:
            issue_key: Jira issue key
            fields: Fields to update (dict)
        """
        self._check_config()

        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers=self.headers,
                    json={"fields": fields},
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("jira_issue_updated", issue_key=issue_key, fields=list(fields.keys()))

        except Exception as e:
            logger.error("jira_update_issue_failed", issue_key=issue_key, error=str(e))
            raise

    async def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
        comment: Optional[str] = None
    ) -> None:
        """
        Transition issue to new status.

        Args:
            issue_key: Jira issue key
            transition_id: Transition ID
            comment: Optional comment to add during transition
        """
        self._check_config()

        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}/transitions"

        payload: Dict[str, Any] = {
            "transition": {"id": transition_id}
        }

        if comment:
            payload["update"] = {
                "comment": [
                    {
                        "add": {
                            "body": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {"type": "text", "text": comment}
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                ]
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

                logger.info("jira_issue_transitioned", issue_key=issue_key, transition_id=transition_id)

        except Exception as e:
            logger.error("jira_transition_failed", issue_key=issue_key, error=str(e))
            raise

    async def add_remote_link(
        self,
        issue_key: str,
        url: str,
        title: str,
        relationship: str = "relates to"
    ) -> Dict[str, Any]:
        """
        Add a remote link to an issue (e.g., GitHub PR link).

        Args:
            issue_key: Jira issue key
            url: URL to link
            title: Link title
            relationship: Link relationship

        Returns:
            API response dict
        """
        self._check_config()

        api_url = f"{self.jira_url}/rest/api/3/issue/{issue_key}/remotelink"

        payload = {
            "object": {
                "url": url,
                "title": title
            },
            "relationship": relationship
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info(
                    "jira_remote_link_added",
                    issue_key=issue_key,
                    link_url=url,
                    link_title=title
                )

                return response.json()

        except Exception as e:
            logger.error("jira_add_link_failed", issue_key=issue_key, url=url, error=str(e))
            raise

    async def assign_issue(
        self,
        issue_key: str,
        account_id: Optional[str] = None
    ) -> None:
        """
        Assign issue to a user.

        Args:
            issue_key: Jira issue key
            account_id: User account ID (None to unassign)
        """
        self._check_config()

        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}/assignee"

        payload = {"accountId": account_id} if account_id else {"accountId": None}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("jira_issue_assigned", issue_key=issue_key, account_id=account_id)

        except Exception as e:
            logger.error("jira_assign_failed", issue_key=issue_key, error=str(e))
            raise


# Global client instance
jira_client = JiraClient()
