"""GitHub API client for webhook interactions."""

import os
import httpx
import structlog
from typing import Optional

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
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error("github_api_error", error=str(e))
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
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/issues/comments/{comment_id}/reactions"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={**self.headers, "Accept": "application/vnd.github.squirrel-girl-preview+json"},
                    json={"content": reaction},
                    timeout=30.0
                )
                response.raise_for_status()
                
                logger.info(
                    "github_reaction_added",
                    comment_id=comment_id,
                    reaction=reaction
                )
                
                return response.json()
                
        except Exception as e:
            logger.error("github_reaction_failed", error=str(e))
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


# Global client instance
github_client = GitHubClient()
