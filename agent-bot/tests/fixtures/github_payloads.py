"""GitHub webhook payload fixtures for testing."""

from typing import Any


def github_issue_opened_payload(
    repo: str = "test-org/test-repo",
    issue_number: int = 1,
    title: str = "Test Issue",
    body: str = "Test issue body",
    labels: list[str] | None = None,
    user: str = "testuser",
) -> dict[str, Any]:
    """Create a GitHub issue opened payload."""
    return {
        "action": "opened",
        "issue": {
            "number": issue_number,
            "title": title,
            "body": body,
            "labels": [{"name": label} for label in (labels or [])],
            "user": {"login": user},
            "state": "open",
            "created_at": "2026-01-31T12:00:00Z",
            "updated_at": "2026-01-31T12:00:00Z",
        },
        "repository": {
            "full_name": repo,
            "clone_url": f"https://github.com/{repo}.git",
            "default_branch": "main",
        },
        "sender": {"login": user},
    }


def github_issue_edited_payload(
    repo: str = "test-org/test-repo",
    issue_number: int = 1,
    title: str = "Updated Issue",
    body: str = "Updated issue body",
    user: str = "testuser",
) -> dict[str, Any]:
    """Create a GitHub issue edited payload."""
    payload = github_issue_opened_payload(
        repo=repo,
        issue_number=issue_number,
        title=title,
        body=body,
        user=user,
    )
    payload["action"] = "edited"
    payload["changes"] = {"body": {"from": "Original body"}}
    return payload


def github_issue_labeled_payload(
    repo: str = "test-org/test-repo",
    issue_number: int = 1,
    label: str = "AI-Fix",
    user: str = "testuser",
) -> dict[str, Any]:
    """Create a GitHub issue labeled payload."""
    return {
        "action": "labeled",
        "issue": {
            "number": issue_number,
            "title": "Test Issue",
            "body": "Test issue body",
            "labels": [{"name": label}],
            "user": {"login": user},
            "state": "open",
        },
        "label": {"name": label},
        "repository": {
            "full_name": repo,
            "clone_url": f"https://github.com/{repo}.git",
            "default_branch": "main",
        },
        "sender": {"login": user},
    }


def github_issue_comment_payload(
    repo: str = "test-org/test-repo",
    issue_number: int = 1,
    comment_id: int = 100,
    body: str = "Test comment",
    user: str = "testuser",
) -> dict[str, Any]:
    """Create a GitHub issue comment payload."""
    return {
        "action": "created",
        "issue": {
            "number": issue_number,
            "title": "Test Issue",
            "body": "Test issue body",
            "labels": [],
            "user": {"login": "original-author"},
            "state": "open",
        },
        "comment": {
            "id": comment_id,
            "body": body,
            "user": {"login": user},
            "created_at": "2026-01-31T12:00:00Z",
        },
        "repository": {
            "full_name": repo,
            "clone_url": f"https://github.com/{repo}.git",
            "default_branch": "main",
        },
        "sender": {"login": user},
    }


def github_pr_opened_payload(
    repo: str = "test-org/test-repo",
    pr_number: int = 1,
    title: str = "Test PR",
    body: str = "Test PR body",
    head: str = "feature-branch",
    base: str = "main",
    user: str = "testuser",
) -> dict[str, Any]:
    """Create a GitHub pull request opened payload."""
    return {
        "action": "opened",
        "pull_request": {
            "number": pr_number,
            "title": title,
            "body": body,
            "head": {"ref": head, "sha": "abc123"},
            "base": {"ref": base, "sha": "def456"},
            "user": {"login": user},
            "state": "open",
            "draft": False,
            "created_at": "2026-01-31T12:00:00Z",
            "updated_at": "2026-01-31T12:00:00Z",
        },
        "repository": {
            "full_name": repo,
            "clone_url": f"https://github.com/{repo}.git",
            "default_branch": "main",
        },
        "sender": {"login": user},
    }


def github_pr_synchronize_payload(
    repo: str = "test-org/test-repo",
    pr_number: int = 1,
    head: str = "feature-branch",
    base: str = "main",
    user: str = "testuser",
) -> dict[str, Any]:
    """Create a GitHub pull request synchronize payload."""
    payload = github_pr_opened_payload(
        repo=repo,
        pr_number=pr_number,
        head=head,
        base=base,
        user=user,
    )
    payload["action"] = "synchronize"
    payload["before"] = "old-sha"
    payload["after"] = "new-sha"
    return payload


def github_pr_review_comment_payload(
    repo: str = "test-org/test-repo",
    pr_number: int = 1,
    comment_id: int = 200,
    body: str = "Review comment",
    path: str = "src/main.py",
    line: int = 10,
    user: str = "reviewer",
) -> dict[str, Any]:
    """Create a GitHub PR review comment payload."""
    return {
        "action": "created",
        "pull_request": {
            "number": pr_number,
            "title": "Test PR",
            "body": "Test PR body",
            "head": {"ref": "feature-branch", "sha": "abc123"},
            "base": {"ref": "main", "sha": "def456"},
            "user": {"login": "author"},
        },
        "comment": {
            "id": comment_id,
            "body": body,
            "path": path,
            "line": line,
            "user": {"login": user},
            "created_at": "2026-01-31T12:00:00Z",
        },
        "repository": {
            "full_name": repo,
            "clone_url": f"https://github.com/{repo}.git",
            "default_branch": "main",
        },
        "sender": {"login": user},
    }


def github_push_payload(
    repo: str = "test-org/test-repo",
    ref: str = "refs/heads/main",
    before: str = "old-sha",
    after: str = "new-sha",
    commits: list[dict[str, str]] | None = None,
    pusher: str = "testuser",
) -> dict[str, Any]:
    """Create a GitHub push payload."""
    if commits is None:
        commits = [
            {"message": "Initial commit", "id": "commit-sha-1"},
            {"message": "Add feature", "id": "commit-sha-2"},
        ]

    return {
        "ref": ref,
        "before": before,
        "after": after,
        "commits": commits,
        "pusher": {"name": pusher},
        "repository": {
            "full_name": repo,
            "clone_url": f"https://github.com/{repo}.git",
            "default_branch": "main",
        },
        "sender": {"login": pusher},
    }
