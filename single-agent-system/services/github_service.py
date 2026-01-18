"""
GitHub Service
==============
Real integration with GitHub API using PyGithub.
"""

import structlog
from github import Github, GithubException
from typing import List, Dict, Any, Optional

from config import settings

logger = structlog.get_logger(__name__)


class GitHubService:
    """Service for interacting with GitHub API."""
    
    def __init__(self):
        """Initialize GitHub client."""
        self.client = Github(settings.github.token)
        self.org = settings.github.org
        logger.info("github_service_initialized", org=self.org)
    
    def search_code(self, query: str, org: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search code across repositories.
        
        Args:
            query: Search query string
            org: Organization to search in (defaults to configured org)
            
        Returns:
            List of search results with repo and file info
        """
        target_org = org or self.org
        full_query = f"{query} org:{target_org}"
        
        try:
            results = self.client.search_code(full_query)
            return [
                {
                    "repository": {
                        "name": item.repository.name,
                        "full_name": item.repository.full_name,
                        "url": item.repository.html_url,
                    },
                    "path": item.path,
                    "name": item.name,
                    "url": item.html_url,
                    "score": getattr(item, "score", 1.0),
                }
                for item in list(results)[:20]
            ]
        except GithubException as e:
            logger.error("github_search_failed", query=query, error=str(e))
            return []
    
    def get_repo(self, repo_name: str) -> Optional[Any]:
        """Get a repository by name.
        
        Args:
            repo_name: Repository name (can be org/repo or just repo)
            
        Returns:
            Repository object or None
        """
        full_name = repo_name if "/" in repo_name else f"{self.org}/{repo_name}"
        try:
            return self.client.get_repo(full_name)
        except GithubException as e:
            logger.error("github_repo_not_found", repo=full_name, error=str(e))
            return None
    
    def get_repo_tree(self, repo_name: str, branch: str = "main") -> Dict[str, Any]:
        """Get repository file tree.
        
        Args:
            repo_name: Repository name
            branch: Branch to get tree from
            
        Returns:
            Tree structure with files and directories
        """
        repo = self.get_repo(repo_name)
        if not repo:
            return {"tree": []}
        
        try:
            tree = repo.get_git_tree(branch, recursive=True)
            return {
                "sha": tree.sha,
                "tree": [
                    {
                        "path": item.path,
                        "type": item.type,
                        "size": getattr(item, "size", 0),
                    }
                    for item in tree.tree
                ]
            }
        except GithubException as e:
            logger.error("github_tree_failed", repo=repo_name, error=str(e))
            return {"tree": []}
    
    def get_file_content(self, repo_name: str, path: str, branch: str = "main") -> Optional[str]:
        """Get file content from repository.
        
        Args:
            repo_name: Repository name
            path: File path within repo
            branch: Branch to get file from
            
        Returns:
            File content as string or None
        """
        repo = self.get_repo(repo_name)
        if not repo:
            return None
        
        try:
            content = repo.get_contents(path, ref=branch)
            if isinstance(content, list):
                return None  # It's a directory
            return content.decoded_content.decode("utf-8")
        except GithubException as e:
            logger.error("github_file_not_found", repo=repo_name, path=path, error=str(e))
            return None
    
    def create_branch(self, repo_name: str, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch.
        
        Args:
            repo_name: Repository name
            branch_name: New branch name
            from_branch: Source branch
            
        Returns:
            True if successful
        """
        if settings.execution.dry_run:
            logger.info("dry_run_create_branch", repo=repo_name, branch=branch_name)
            return True
            
        repo = self.get_repo(repo_name)
        if not repo:
            return False
        
        try:
            source = repo.get_branch(from_branch)
            repo.create_git_ref(f"refs/heads/{branch_name}", source.commit.sha)
            logger.info("branch_created", repo=repo_name, branch=branch_name)
            return True
        except GithubException as e:
            logger.error("github_branch_failed", repo=repo_name, branch=branch_name, error=str(e))
            return False
    
    def create_or_update_file(
        self,
        repo_name: str,
        path: str,
        content: str,
        message: str,
        branch: str
    ) -> bool:
        """Create or update a file in repository.
        
        Args:
            repo_name: Repository name
            path: File path
            content: File content
            message: Commit message
            branch: Target branch
            
        Returns:
            True if successful
        """
        if settings.execution.dry_run:
            logger.info("dry_run_update_file", repo=repo_name, path=path)
            return True
            
        repo = self.get_repo(repo_name)
        if not repo:
            return False
        
        try:
            # Check if file exists
            try:
                existing = repo.get_contents(path, ref=branch)
                sha = existing.sha
                repo.update_file(path, message, content, sha, branch=branch)
                logger.info("file_updated", repo=repo_name, path=path)
            except GithubException:
                # File doesn't exist, create it
                repo.create_file(path, message, content, branch=branch)
                logger.info("file_created", repo=repo_name, path=path)
            return True
        except GithubException as e:
            logger.error("github_file_update_failed", repo=repo_name, path=path, error=str(e))
            return False
    
    def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Create a pull request.
        
        Args:
            repo_name: Repository name
            title: PR title
            body: PR description
            head: Head branch
            base: Base branch
            draft: Create as draft PR
            
        Returns:
            PR info dict or None
        """
        if settings.execution.dry_run:
            logger.info("dry_run_create_pr", repo=repo_name, title=title)
            return {"number": 0, "html_url": "https://github.com/dry-run"}
            
        repo = self.get_repo(repo_name)
        if not repo:
            return None
        
        try:
            pr = repo.create_pull(title=title, body=body, head=head, base=base, draft=draft)
            logger.info("pr_created", repo=repo_name, pr_number=pr.number)
            return {
                "number": pr.number,
                "html_url": pr.html_url,
                "state": pr.state,
            }
        except GithubException as e:
            logger.error("github_pr_failed", repo=repo_name, error=str(e))
            return None
    
    def get_workflow_runs(self, repo_name: str, head_sha: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get workflow runs for a repository.
        
        Args:
            repo_name: Repository name
            head_sha: Filter by commit SHA
            
        Returns:
            List of workflow run info
        """
        repo = self.get_repo(repo_name)
        if not repo:
            return []
        
        try:
            runs = repo.get_workflow_runs(head_sha=head_sha) if head_sha else repo.get_workflow_runs()
            return [
                {
                    "id": run.id,
                    "name": run.name,
                    "status": run.status,
                    "conclusion": run.conclusion,
                    "head_sha": run.head_sha,
                    "url": run.html_url,
                }
                for run in list(runs)[:10]
            ]
        except GithubException as e:
            logger.error("github_workflow_runs_failed", repo=repo_name, error=str(e))
            return []
