"""Git repository and operation models."""

from dataclasses import dataclass
from typing import Optional

from types.enums import GitOperation


@dataclass
class GitRepository:
    """A Git repository."""
    owner: str
    name: str
    full_name: str
    clone_url: str
    default_branch: str = "main"

    @classmethod
    def from_full_name(cls, full_name: str) -> "GitRepository":
        """Create from full_name (owner/repo)."""
        parts = full_name.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid repository name: {full_name}")
        owner, name = parts
        return cls(
            owner=owner,
            name=name,
            full_name=full_name,
            clone_url=f"https://github.com/{full_name}.git",
        )


@dataclass
class GitOperationResult:
    """Result of a Git operation."""
    operation: GitOperation
    success: bool
    output: str
    error: Optional[str] = None
    commit_sha: Optional[str] = None
