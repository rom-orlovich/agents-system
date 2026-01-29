import httpx
import structlog
from typing import Dict, Any

logger = structlog.get_logger()


class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def post_pr_comment(
        self, owner: str, repo: str, pr_number: int, comment: str
    ) -> Dict[str, str | int | bool]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json={"body": comment},
                    headers=self.headers,
                    timeout=30.0,
                )

                response.raise_for_status()
                data = response.json()

                logger.info(
                    "github_pr_comment_posted",
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                    comment_id=data.get("id"),
                )

                return {
                    "success": True,
                    "comment_id": data.get("id"),
                    "message": "Comment posted successfully",
                }
            except httpx.HTTPStatusError as e:
                logger.error(
                    "github_pr_comment_failed",
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                    status_code=e.response.status_code,
                    error=str(e),
                )
                return {
                    "success": False,
                    "comment_id": None,
                    "message": f"Failed to post comment: {e.response.status_code}",
                    "error": str(e),
                }
            except Exception as e:
                logger.error(
                    "github_pr_comment_exception",
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                    error=str(e),
                )
                return {
                    "success": False,
                    "comment_id": None,
                    "message": "Failed to post comment",
                    "error": str(e),
                }

    async def post_issue_comment(
        self, owner: str, repo: str, issue_number: int, comment: str
    ) -> Dict[str, str | int | bool]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json={"body": comment},
                    headers=self.headers,
                    timeout=30.0,
                )

                response.raise_for_status()
                data = response.json()

                logger.info(
                    "github_issue_comment_posted",
                    owner=owner,
                    repo=repo,
                    issue_number=issue_number,
                    comment_id=data.get("id"),
                )

                return {
                    "success": True,
                    "comment_id": data.get("id"),
                    "message": "Comment posted successfully",
                }
            except Exception as e:
                logger.error(
                    "github_issue_comment_failed",
                    owner=owner,
                    repo=repo,
                    issue_number=issue_number,
                    error=str(e),
                )
                return {
                    "success": False,
                    "comment_id": None,
                    "message": "Failed to post comment",
                    "error": str(e),
                }

    async def get_pr_details(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, str | int | bool | None]:
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, headers=self.headers, timeout=30.0
                )

                response.raise_for_status()
                data = response.json()

                return {
                    "success": True,
                    "pr_number": data.get("number"),
                    "title": data.get("title"),
                    "body": data.get("body"),
                    "state": data.get("state"),
                    "merged": data.get("merged"),
                }
            except Exception as e:
                logger.error(
                    "github_pr_details_failed",
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                    error=str(e),
                )
                return {
                    "success": False,
                    "pr_number": None,
                    "title": None,
                    "body": None,
                    "state": None,
                    "merged": None,
                    "error": str(e),
                }

    async def get_issue_details(
        self, owner: str, repo: str, issue_number: int
    ) -> Dict[str, str | int | bool | None]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, headers=self.headers, timeout=30.0
                )

                response.raise_for_status()
                data = response.json()

                return {
                    "success": True,
                    "issue_number": data.get("number"),
                    "title": data.get("title"),
                    "body": data.get("body"),
                    "state": data.get("state"),
                }
            except Exception as e:
                logger.error(
                    "github_issue_details_failed",
                    owner=owner,
                    repo=repo,
                    issue_number=issue_number,
                    error=str(e),
                )
                return {
                    "success": False,
                    "issue_number": None,
                    "title": None,
                    "body": None,
                    "state": None,
                    "error": str(e),
                }
