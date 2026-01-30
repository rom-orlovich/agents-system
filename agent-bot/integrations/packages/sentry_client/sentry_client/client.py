import httpx
import structlog

from .models import (
    AddCommentInput,
    AddCommentResponse,
    UpdateIssueStatusInput,
    UpdateIssueStatusResponse,
    GetIssueInput,
    SentryIssueResponse,
    AssignIssueInput,
    AssignIssueResponse,
    AddTagInput,
    AddTagResponse,
)
from .exceptions import (
    SentryAuthenticationError,
    SentryNotFoundError,
    SentryValidationError,
    SentryRateLimitError,
    SentryServerError,
    SentryClientError,
)

logger = structlog.get_logger()


class SentryClient:
    def __init__(
        self, auth_token: str, org_slug: str, project_slug: str, timeout: float = 30.0
    ):
        self.auth_token = auth_token
        self.org_slug = org_slug
        self.project_slug = project_slug
        self.timeout = timeout
        self.base_url = "https://sentry.io/api/0"

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }

    def _handle_error(self, response: httpx.Response, context: str) -> None:
        status_code = response.status_code

        if status_code == 401:
            raise SentryAuthenticationError(f"{context}: Invalid auth token")
        elif status_code == 404:
            raise SentryNotFoundError(f"{context}: Resource not found")
        elif status_code == 400:
            raise SentryValidationError(f"{context}: {response.text}")
        elif status_code == 429:
            raise SentryRateLimitError(f"{context}: Rate limit exceeded")
        elif status_code >= 500:
            raise SentryServerError(f"{context}: Server error ({status_code})")
        else:
            raise SentryClientError(f"{context}: HTTP {status_code} - {response.text}")

    async def add_comment(self, input_data: AddCommentInput) -> AddCommentResponse:
        url = f"{self.base_url}/issues/{input_data.issue_id}/notes/"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json={"text": input_data.comment},
                    timeout=self.timeout,
                )
                response.raise_for_status()

                result = response.json()
                logger.info(
                    "sentry_comment_added",
                    issue_id=input_data.issue_id,
                    comment_id=result.get("id"),
                )

                return AddCommentResponse(
                    success=True,
                    comment_id=str(result.get("id")),
                    message=f"Successfully added comment to issue {input_data.issue_id}",
                )
            except httpx.HTTPStatusError as e:
                self._handle_error(e.response, "add_comment")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "sentry_comment_failed",
                    issue_id=input_data.issue_id,
                    error=str(e),
                )
                return AddCommentResponse(
                    success=False,
                    comment_id=None,
                    message=f"Error adding comment: {str(e)}",
                )

    async def update_issue_status(
        self, input_data: UpdateIssueStatusInput
    ) -> UpdateIssueStatusResponse:
        url = f"{self.base_url}/issues/{input_data.issue_id}/"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    url,
                    headers=self._get_headers(),
                    json={"status": input_data.status},
                    timeout=self.timeout,
                )
                response.raise_for_status()

                logger.info(
                    "sentry_status_updated",
                    issue_id=input_data.issue_id,
                    status=input_data.status,
                )

                return UpdateIssueStatusResponse(
                    success=True,
                    message=f"Successfully updated status to {input_data.status}",
                )
            except httpx.HTTPStatusError as e:
                self._handle_error(e.response, "update_issue_status")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "sentry_status_update_failed",
                    issue_id=input_data.issue_id,
                    error=str(e),
                )
                return UpdateIssueStatusResponse(
                    success=False, message=f"Error updating status: {str(e)}"
                )

    async def get_issue(self, input_data: GetIssueInput) -> SentryIssueResponse:
        url = f"{self.base_url}/issues/{input_data.issue_id}/"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, headers=self._get_headers(), timeout=self.timeout
                )
                response.raise_for_status()

                result = response.json()

                return SentryIssueResponse(
                    success=True,
                    issue_id=input_data.issue_id,
                    title=result.get("title"),
                    status=result.get("status"),
                    level=result.get("level"),
                    culprit=result.get("culprit"),
                )
            except httpx.HTTPStatusError as e:
                self._handle_error(e.response, "get_issue")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "sentry_get_issue_failed",
                    issue_id=input_data.issue_id,
                    error=str(e),
                )
                return SentryIssueResponse(
                    success=False,
                    issue_id=None,
                    title=None,
                    status=None,
                    level=None,
                    culprit=None,
                )

    async def assign_issue(self, input_data: AssignIssueInput) -> AssignIssueResponse:
        url = f"{self.base_url}/issues/{input_data.issue_id}/"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    url,
                    headers=self._get_headers(),
                    json={"assignedTo": input_data.assignee},
                    timeout=self.timeout,
                )
                response.raise_for_status()

                logger.info(
                    "sentry_issue_assigned",
                    issue_id=input_data.issue_id,
                    assignee=input_data.assignee,
                )

                return AssignIssueResponse(
                    success=True,
                    message=f"Successfully assigned issue to {input_data.assignee}",
                )
            except httpx.HTTPStatusError as e:
                self._handle_error(e.response, "assign_issue")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "sentry_assign_failed",
                    issue_id=input_data.issue_id,
                    error=str(e),
                )
                return AssignIssueResponse(
                    success=False, message=f"Error assigning issue: {str(e)}"
                )

    async def add_tag(self, input_data: AddTagInput) -> AddTagResponse:
        url = f"{self.base_url}/issues/{input_data.issue_id}/tags/"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json={"key": input_data.key, "value": input_data.value},
                    timeout=self.timeout,
                )
                response.raise_for_status()

                logger.info(
                    "sentry_tag_added",
                    issue_id=input_data.issue_id,
                    key=input_data.key,
                    value=input_data.value,
                )

                return AddTagResponse(
                    success=True,
                    message=f"Successfully added tag {input_data.key}={input_data.value}",
                )
            except httpx.HTTPStatusError as e:
                self._handle_error(e.response, "add_tag")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "sentry_add_tag_failed", issue_id=input_data.issue_id, error=str(e)
                )
                return AddTagResponse(
                    success=False, message=f"Error adding tag: {str(e)}"
                )
