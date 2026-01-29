import httpx
import os
import structlog
from typing import Dict, Any

logger = structlog.get_logger()


class JiraClient:
    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
        timeout: int = 30,
    ):
        self.base_url = base_url or os.getenv("JIRA_BASE_URL", "")
        self.email = email or os.getenv("JIRA_EMAIL", "")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN", "")
        self.timeout = timeout

        if not self.base_url or not self.email or not self.api_token:
            raise ValueError("Jira credentials not configured")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        payload = {"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]}}

        async with httpx.AsyncClient(auth=(self.email, self.api_token), timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error("jira_add_comment_failed", issue_key=issue_key, error=str(e))
                raise

    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"

        async with httpx.AsyncClient(auth=(self.email, self.api_token), timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error("jira_get_issue_failed", issue_key=issue_key, error=str(e))
                raise

    async def transition_issue(self, issue_key: str, transition_id: str) -> None:
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
        payload = {"transition": {"id": transition_id}}

        async with httpx.AsyncClient(auth=(self.email, self.api_token), timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
            except httpx.HTTPError as e:
                logger.error(
                    "jira_transition_failed",
                    issue_key=issue_key,
                    transition_id=transition_id,
                    error=str(e),
                )
                raise

    async def create_issue(
        self, project_key: str, summary: str, description: str, issue_type: str
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "issuetype": {"name": issue_type},
            }
        }

        async with httpx.AsyncClient(auth=(self.email, self.api_token), timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error("jira_create_issue_failed", error=str(e))
                raise
