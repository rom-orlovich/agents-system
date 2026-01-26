"""GitHub API client for webhook interactions and code analysis."""

import os
import httpx
import structlog
from typing import Optional, Dict, Any, List

logger = structlog.get_logger()


class GitHubClient:
    """Client for interacting with GitHub API."""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client with optional token."""
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Claude-Code-Agent"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
            logger.debug("github_client_initialized", has_token=True, token_length=len(self.token))
        else:
            logger.warning(
                "github_client_no_token",
                message="GITHUB_TOKEN not found in environment. GitHub API calls will fail."
            )
    
    async def post_issue_comment(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        comment_body: str
    ) -> dict:
        """
        Post a comment to a GitHub issue.
        
        Args:
            repo_owner: Repository owner (username or org)
            repo_name: Repository name
            issue_number: Issue number
            comment_body: Comment text
            
        Returns:
            API response dict
        """
        if not self.token:
            logger.warning("github_comment_skipped_no_token", repo=f"{repo_owner}/{repo_name}", issue=issue_number)
            raise ValueError("GITHUB_TOKEN not configured - cannot post comment")
        
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={"body": comment_body},
                    timeout=30.0
                )
                response.raise_for_status()
                
                logger.info(
                    "github_comment_posted",
                    repo=f"{repo_owner}/{repo_name}",
                    issue=issue_number
                )
                
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(
                "github_comment_failed",
                status_code=e.response.status_code,
                error=str(e),
                repo=f"{repo_owner}/{repo_name}",
                issue=issue_number
            )
            raise
        except Exception as e:
            logger.error("github_api_error", error=str(e), repo=f"{repo_owner}/{repo_name}", issue=issue_number)
            raise
    
    async def post_pr_comment(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        comment_body: str
    ) -> dict:
        """
        Post a comment to a GitHub pull request.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            pr_number: PR number
            comment_body: Comment text
            
        Returns:
            API response dict
        """
        # PR comments use the same endpoint as issues
        return await self.post_issue_comment(
            repo_owner,
            repo_name,
            pr_number,
            comment_body
        )
    
    async def add_reaction(
        self,
        repo_owner: str,
        repo_name: str,
        comment_id: int,
        reaction: str = "+1"
    ) -> dict:
        """
        Add a reaction to a comment.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            comment_id: Comment ID
            reaction: Reaction type (+1, -1, laugh, confused, heart, hooray, rocket, eyes)
            
        Returns:
            API response dict
        """
        if not self.token:
            logger.warning("github_reaction_skipped_no_token", comment_id=comment_id)
            raise ValueError("GITHUB_TOKEN not configured - cannot add reaction")
        
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/issues/comments/{comment_id}/reactions"
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    **self.headers,
                    "Accept": "application/vnd.github+json"
                }
                response = await client.post(
                    url,
                    headers=headers,
                    json={"content": reaction},
                    timeout=30.0
                )
                response.raise_for_status()
                
                response_data = response.json()
                
                if not response_data.get("id"):
                    logger.warning(
                        "github_reaction_response_missing_id",
                        comment_id=comment_id,
                        reaction=reaction,
                        response_status=response.status_code,
                        response_body=response.text[:200]
                    )
                
                logger.info(
                    "github_reaction_added",
                    comment_id=comment_id,
                    reaction=reaction,
                    response_id=response_data.get("id"),
                    response_content=response_data.get("content"),
                    user_login=response_data.get("user", {}).get("login") if isinstance(response_data.get("user"), dict) else None
                )
                
                return response_data
                
        except httpx.HTTPStatusError as e:
            logger.error(
                "github_reaction_failed",
                status_code=e.response.status_code,
                error=str(e),
                comment_id=comment_id
            )
            raise
        except Exception as e:
            logger.error("github_reaction_failed", error=str(e), comment_id=comment_id)
            raise
    
    async def update_issue_labels(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        labels: list[str]
    ) -> dict:
        """
        Update labels on an issue.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            issue_number: Issue number
            labels: List of label names
            
        Returns:
            API response dict
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_number}/labels"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={"labels": labels},
                    timeout=30.0
                )
                response.raise_for_status()
                
                logger.info(
                    "github_labels_updated",
                    issue=issue_number,
                    labels=labels
                )
                
                return response.json()
                
        except Exception as e:
            logger.error("github_labels_failed", error=str(e))
            raise

    async def get_repository_info(
        self,
        repo_owner: str,
        repo_name: str
    ) -> Dict[str, Any]:
        """
        Get repository information.

        Args:
            repo_owner: Repository owner
            repo_name: Repository name

        Returns:
            Repository data dict
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("github_repo_info_fetched", repo=f"{repo_owner}/{repo_name}")
                return response.json()

        except Exception as e:
            logger.error("github_get_repo_failed", repo=f"{repo_owner}/{repo_name}", error=str(e))
            raise

    async def get_issue(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int
    ) -> Dict[str, Any]:
        """
        Get issue details.

        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            issue_number: Issue number

        Returns:
            Issue data dict
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_number}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("github_issue_fetched", repo=f"{repo_owner}/{repo_name}", issue=issue_number)
                return response.json()

        except Exception as e:
            logger.error("github_get_issue_failed", repo=f"{repo_owner}/{repo_name}", issue=issue_number, error=str(e))
            raise

    async def create_pull_request(
        self,
        repo_owner: str,
        repo_name: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
        draft: bool = True
    ) -> Dict[str, Any]:
        """
        Create a pull request.

        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            title: PR title
            head: Branch name to merge from
            base: Branch name to merge into
            body: Optional PR description
            draft: Create as draft PR (default: True)

        Returns:
            PR data dict
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/pulls"

        payload: Dict[str, Any] = {
            "title": title,
            "head": head,
            "base": base,
            "draft": draft
        }

        if body:
            payload["body"] = body

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                pr_data = response.json()

                logger.info(
                    "github_pr_created",
                    repo=f"{repo_owner}/{repo_name}",
                    pr=pr_data.get("number"),
                    url=pr_data.get("html_url")
                )

                return pr_data

        except Exception as e:
            logger.error("github_create_pr_failed", repo=f"{repo_owner}/{repo_name}", error=str(e))
            raise

    async def get_repository_languages(
        self,
        repo_owner: str,
        repo_name: str
    ) -> Dict[str, int]:
        """
        Get programming languages used in repository.

        Args:
            repo_owner: Repository owner
            repo_name: Repository name

        Returns:
            Dict of language name -> bytes of code
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/languages"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("github_languages_fetched", repo=f"{repo_owner}/{repo_name}")
                return response.json()

        except Exception as e:
            logger.error("github_get_languages_failed", repo=f"{repo_owner}/{repo_name}", error=str(e))
            raise

    async def search_code(
        self,
        query: str,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search code in GitHub.

        Args:
            query: Search query
            repo_owner: Optional repository owner to limit search
            repo_name: Optional repository name to limit search
            max_results: Maximum number of results

        Returns:
            List of code search results
        """
        url = f"{self.base_url}/search/code"

        # Build query
        search_query = query
        if repo_owner and repo_name:
            search_query = f"{query} repo:{repo_owner}/{repo_name}"

        params = {
            "q": search_query,
            "per_page": min(max_results, 100)
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()
                items = data.get("items", [])

                logger.info(
                    "github_code_search_complete",
                    query=query,
                    results=len(items)
                )

                return items

        except Exception as e:
            logger.error("github_code_search_failed", query=query, error=str(e))
            raise

    async def get_pull_request(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """
        Get pull request details.

        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            pr_number: PR number

        Returns:
            PR data dict with title, body, state, files changed, etc.
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()

                logger.info("github_pr_fetched", repo=f"{repo_owner}/{repo_name}", pr=pr_number)
                return response.json()

        except Exception as e:
            logger.error("github_get_pr_failed", repo=f"{repo_owner}/{repo_name}", pr=pr_number, error=str(e))
            raise

    async def get_pr_files(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of files changed in a pull request.

        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            pr_number: PR number

        Returns:
            List of file change dicts with filename, additions, deletions, patch, etc.
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/pulls/{pr_number}/files"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()

                files = response.json()
                logger.info(
                    "github_pr_files_fetched",
                    repo=f"{repo_owner}/{repo_name}",
                    pr=pr_number,
                    files_count=len(files)
                )
                return files

        except Exception as e:
            logger.error("github_get_pr_files_failed", repo=f"{repo_owner}/{repo_name}", pr=pr_number, error=str(e))
            raise

    async def get_file_content(
        self,
        repo_owner: str,
        repo_name: str,
        file_path: str,
        ref: Optional[str] = None
    ) -> str:
        """
        Get file content from repository at specific ref/branch.

        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            file_path: Path to file in repository
            ref: Optional git ref (branch, tag, commit SHA). Defaults to default branch.

        Returns:
            File content as string (decoded from base64)
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/contents/{file_path}"
        
        params = {}
        if ref:
            params["ref"] = ref

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()
                import base64
                content_b64 = data.get("content", "")
                content = base64.b64decode(content_b64).decode("utf-8")

                logger.info(
                    "github_file_content_fetched",
                    repo=f"{repo_owner}/{repo_name}",
                    file=file_path,
                    ref=ref or "default"
                )
                return content

        except Exception as e:
            logger.error(
                "github_get_file_content_failed",
                repo=f"{repo_owner}/{repo_name}",
                file=file_path,
                ref=ref,
                error=str(e)
            )
            raise


# Global client instance
github_client = GitHubClient()
