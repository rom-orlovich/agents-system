"""
GitHub API Client
=================
Wrapper for GitHub API operations.
"""

import structlog
from github import Github

from shared.config import get_settings

logger = structlog.get_logger(__name__)


class GitHubClient:
    """GitHub API Client."""

    def __init__(self):
        settings = get_settings()
        self.client = Github(settings.github.token)
        self.org = settings.github.org

    def get_repo(self, repo_name: str):
        """Get a repository by name."""
        full_name = f"{self.org}/{repo_name}" if "/" not in repo_name else repo_name
        return self.client.get_repo(full_name)

    def create_branch(self, repo_name: str, branch_name: str, base_branch: str = "main") -> str:
        """Create a new branch from base branch."""
        repo = self.get_repo(repo_name)
        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        repo.create_git_ref(f"refs/heads/{branch_name}", base_ref.object.sha)
        logger.info("Created branch", repo=repo_name, branch=branch_name)
        return branch_name

    def create_pr(
        self,
        repo_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False,
    ) -> str:
        """Create a Pull Request and return its URL."""
        repo = self.get_repo(repo_name)

        pr = repo.create_pull(
            title=title,
            body=body,
            head=head,
            base=base,
            maintainer_can_modify=True,
            draft=draft,
        )

        # Add labels
        pr.add_to_labels("automated", "claude-agent")

        logger.info("Created PR", repo=repo_name, pr_number=pr.number, url=pr.html_url)
        return pr.html_url

    def get_pr(self, repo_name: str, pr_number: int):
        """Get a PR by number."""
        repo = self.get_repo(repo_name)
        return repo.get_pull(pr_number)

    def get_pr_files(self, repo_name: str, pr_number: int) -> list:
        """Get list of files in a PR."""
        pr = self.get_pr(repo_name, pr_number)
        return [f.filename for f in pr.get_files()]

    def get_file_content(self, repo_name: str, path: str, ref: str = "main") -> str:
        """Get file content from repository."""
        repo = self.get_repo(repo_name)
        content = repo.get_contents(path, ref=ref)
        return content.decoded_content.decode("utf-8")

    def add_pr_comment(self, repo_name: str, pr_number: int, comment: str):
        """Add a comment to a PR."""
        pr = self.get_pr(repo_name, pr_number)
        pr.create_issue_comment(comment)
        logger.info("Added PR comment", repo=repo_name, pr_number=pr_number)
