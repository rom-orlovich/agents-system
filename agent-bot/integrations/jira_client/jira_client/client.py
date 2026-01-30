import httpx
import structlog
from base64 import b64encode
from typing import Any

from .models import (
    AddCommentInput,
    AddCommentResponse,
    GetIssueInput,
    JiraIssueResponse,
    CreateIssueInput,
    CreateIssueResponse,
    TransitionIssueInput,
    TransitionIssueResponse,
)
from .exceptions import (
    JiraAuthenticationError,
    JiraNotFoundError,
    JiraValidationError,
    JiraRateLimitError,
    JiraServerError,
    JiraClientError,
)

logger = structlog.get_logger()


class JiraClient:
    def __init__(self, email: str, api_token: str, domain: str, timeout: float = 30.0):
        self.email = email
        self.api_token = api_token
        self.domain = domain
        self.timeout = timeout
        self.base_url = f"https://{domain}/rest/api/3"

    def _get_auth_header(self) -> str:
        credentials = f"{self.email}:{self.api_token}"
        encoded = b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _handle_error(self, response: httpx.Response, context: str) -> None:
        status_code = response.status_code

        if status_code == 401:
            raise JiraAuthenticationError(f"{context}: Invalid credentials")
        elif status_code == 404:
            raise JiraNotFoundError(f"{context}: Resource not found")
        elif status_code == 400:
            raise JiraValidationError(f"{context}: {response.text}")
        elif status_code == 429:
            raise JiraRateLimitError(f"{context}: Rate limit exceeded")
        elif status_code >= 500:
            raise JiraServerError(f"{context}: Server error ({status_code})")
        else:
            raise JiraClientError(f"{context}: HTTP {status_code} - {response.text}")

    async def add_comment(self, input_data: AddCommentInput) -> AddCommentResponse:
        url = f"{self.base_url}/issue/{input_data.issue_key}/comment"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json={"body": input_data.comment},
                    timeout=self.timeout,
                )
                response.raise_for_status()

                result = response.json()
                logger.info(
                    "jira_comment_added",
                    issue_key=input_data.issue_key,
                    comment_id=result.get("id"),
                )

                return AddCommentResponse(
                    success=True,
                    comment_id=str(result.get("id")),
                    message=f"Successfully added comment to {input_data.issue_key}",
                )
            except httpx.HTTPStatusError as e:
                self._handle_error(e.response, "add_comment")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "jira_comment_failed",
                    issue_key=input_data.issue_key,
                    error=str(e),
                )
                return AddCommentResponse(
                    success=False,
                    comment_id=None,
                    message=f"Error adding comment: {str(e)}",
                )

    async def get_issue(self, input_data: GetIssueInput) -> JiraIssueResponse:
        url = f"{self.base_url}/issue/{input_data.issue_key}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, headers=self._get_headers(), timeout=self.timeout
                )
                response.raise_for_status()

                result = response.json()
                fields = result.get("fields", {})

                return JiraIssueResponse(
                    success=True,
                    issue_key=input_data.issue_key,
                    title=fields.get("summary"),
                    status=fields.get("status", {}).get("name"),
                    description=fields.get("description"),
                )
            except httpx.HTTPStatusError as e:
                self._handle_error(e.response, "get_issue")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "jira_get_issue_failed",
                    issue_key=input_data.issue_key,
                    error=str(e),
                )
                return JiraIssueResponse(
                    success=False,
                    issue_key=None,
                    title=None,
                    status=None,
                    description=None,
                )

    async def create_issue(self, input_data: CreateIssueInput) -> CreateIssueResponse:
        url = f"{self.base_url}/issue"
        payload = {
            "fields": {
                "project": {"key": input_data.project_key},
                "summary": input_data.summary,
                "description": input_data.description,
                "issuetype": {"name": input_data.issue_type},
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                result = response.json()
                issue_key = result.get("key")
                logger.info(
                    "jira_issue_created",
                    issue_key=issue_key,
                    project=input_data.project_key,
                )

                return CreateIssueResponse(
                    success=True,
                    issue_key=issue_key,
                    message=f"Successfully created issue {issue_key}",
                )
            except httpx.HTTPStatusError as e:
                self._handle_error(e.response, "create_issue")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "jira_create_issue_failed",
                    project=input_data.project_key,
                    error=str(e),
                )
                return CreateIssueResponse(
                    success=False,
                    issue_key=None,
                    message=f"Error creating issue: {str(e)}",
                )

    async def transition_issue(
        self, input_data: TransitionIssueInput
    ) -> TransitionIssueResponse:
        url = f"{self.base_url}/issue/{input_data.issue_key}/transitions"
        payload = {"transition": {"id": input_data.transition_id}}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                logger.info(
                    "jira_issue_transitioned",
                    issue_key=input_data.issue_key,
                    transition_id=input_data.transition_id,
                )

                return TransitionIssueResponse(
                    success=True,
                    message=f"Successfully transitioned {input_data.issue_key}",
                )
            except httpx.HTTPStatusError as e:
                self._handle_error(e.response, "transition_issue")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "jira_transition_failed",
                    issue_key=input_data.issue_key,
                    error=str(e),
                )
                return TransitionIssueResponse(
                    success=False, message=f"Error transitioning issue: {str(e)}"
                )
