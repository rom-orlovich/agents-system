"""Tests for GitHub webhook business logic.

Tests processing of GitHub webhook events.
"""

import sys
from pathlib import Path

from .fixtures import (
    github_issue_opened_payload,
    github_issue_comment_payload,
    github_pr_opened_payload,
    github_pr_review_comment_payload,
    github_push_payload,
)

sys.path.insert(0, str(Path(__file__).parent.parent))

from webhooks.github.events import should_process_event, extract_task_info


class TestGitHubEventFiltering:
    """Tests for GitHub event type filtering."""

    def test_issue_opened_is_processed(self):
        """Business requirement: New issues trigger agents."""
        assert should_process_event("issues", "opened") is True

    def test_issue_edited_is_processed(self):
        """Business requirement: Edited issues may need attention."""
        assert should_process_event("issues", "edited") is True

    def test_issue_labeled_is_processed(self):
        """Business requirement: Labels can trigger automation."""
        assert should_process_event("issues", "labeled") is True

    def test_issue_comment_created_is_processed(self):
        """Business requirement: Comments may need response."""
        assert should_process_event("issue_comment", "created") is True

    def test_pr_opened_is_processed(self):
        """Business requirement: New PRs need review."""
        assert should_process_event("pull_request", "opened") is True

    def test_pr_synchronize_is_processed(self):
        """Business requirement: Code push updates review context."""
        assert should_process_event("pull_request", "synchronize") is True

    def test_pr_reopened_is_processed(self):
        """Business requirement: Reopened PRs need attention."""
        assert should_process_event("pull_request", "reopened") is True

    def test_pr_review_comment_is_processed(self):
        """Business requirement: Review comments need processing."""
        assert should_process_event("pull_request_review_comment", "created") is True

    def test_push_is_processed(self):
        """Business requirement: Push events processed."""
        assert should_process_event("push", None) is True

    def test_unsupported_event_ignored(self):
        """Business requirement: Only relevant events processed."""
        assert should_process_event("fork", None) is False
        assert should_process_event("star", "created") is False
        assert should_process_event("watch", "started") is False

    def test_unsupported_action_ignored(self):
        """Business requirement: Only relevant actions processed."""
        assert should_process_event("issues", "closed") is False
        assert should_process_event("issues", "deleted") is False
        assert should_process_event("pull_request", "closed") is False


class TestGitHubTaskExtraction:
    """Tests for extracting task info from GitHub payloads."""

    def test_issue_opened_extracts_task_info(self):
        """Business requirement: Issue data becomes task info."""
        payload = github_issue_opened_payload(
            repo="myorg/myrepo",
            issue_number=123,
            title="Fix authentication bug",
            body="Users can't log in",
        )

        task_info = extract_task_info("issues", payload)

        assert task_info["source"] == "github"
        assert task_info["event_type"] == "issues"
        assert task_info["action"] == "opened"
        assert task_info["repository"]["full_name"] == "myorg/myrepo"
        assert task_info["issue"]["number"] == 123
        assert task_info["issue"]["title"] == "Fix authentication bug"

    def test_issue_comment_extracts_comment_info(self):
        """Business requirement: Comment data preserved."""
        payload = github_issue_comment_payload(
            repo="myorg/myrepo",
            issue_number=123,
            comment_id=456,
            body="Please fix this ASAP",
            user="commenter",
        )

        task_info = extract_task_info("issue_comment", payload)

        assert task_info["issue"]["number"] == 123
        assert task_info["comment"]["id"] == 456
        assert task_info["comment"]["body"] == "Please fix this ASAP"
        assert task_info["comment"]["user"] == "commenter"

    def test_pr_opened_extracts_pr_info(self):
        """Business requirement: PR data becomes task info."""
        payload = github_pr_opened_payload(
            repo="myorg/myrepo",
            pr_number=42,
            title="Add new feature",
            head="feature-branch",
            base="main",
        )

        task_info = extract_task_info("pull_request", payload)

        assert task_info["source"] == "github"
        assert task_info["pull_request"]["number"] == 42
        assert task_info["pull_request"]["title"] == "Add new feature"
        assert task_info["pull_request"]["head_ref"] == "feature-branch"
        assert task_info["pull_request"]["base_ref"] == "main"

    def test_pr_review_comment_extracts_path_info(self):
        """Business requirement: Code review context preserved."""
        payload = github_pr_review_comment_payload(
            repo="myorg/myrepo",
            pr_number=42,
            comment_id=789,
            body="This needs refactoring",
            path="src/main.py",
            line=25,
        )

        task_info = extract_task_info("pull_request_review_comment", payload)

        assert task_info["comment"]["path"] == "src/main.py"
        assert task_info["comment"]["line"] == 25
        assert task_info["comment"]["body"] == "This needs refactoring"

    def test_push_extracts_commit_info(self):
        """Business requirement: Push commit data extracted."""
        payload = github_push_payload(
            repo="myorg/myrepo",
            ref="refs/heads/main",
            commits=[
                {"message": "Fix bug", "id": "abc123"},
                {"message": "Add tests", "id": "def456"},
            ],
        )

        task_info = extract_task_info("push", payload)

        assert task_info["push"]["ref"] == "refs/heads/main"
        assert len(task_info["push"]["commits"]) == 2
        assert task_info["push"]["commits"][0]["message"] == "Fix bug"

    def test_repository_info_always_included(self):
        """Business requirement: Repository context always present."""
        payload = github_issue_opened_payload(repo="myorg/myrepo")
        task_info = extract_task_info("issues", payload)

        assert "repository" in task_info
        assert task_info["repository"]["full_name"] == "myorg/myrepo"
        assert "clone_url" in task_info["repository"]
        assert "default_branch" in task_info["repository"]

    def test_labels_extracted_from_issue(self):
        """Business requirement: Labels preserved for filtering."""
        payload = github_issue_opened_payload(
            labels=["bug", "AI-Fix", "urgent"],
        )

        task_info = extract_task_info("issues", payload)

        assert "AI-Fix" in task_info["issue"]["labels"]
        assert "bug" in task_info["issue"]["labels"]


class TestSupportedGitHubEvents:
    """Tests for supported GitHub event types."""

    def test_supported_issues_actions(self):
        """Verify all supported issue actions."""
        supported_actions = ["opened", "edited", "labeled"]
        for action in supported_actions:
            assert should_process_event("issues", action) is True

    def test_supported_issue_comment_actions(self):
        """Verify all supported issue comment actions."""
        assert should_process_event("issue_comment", "created") is True

    def test_supported_pr_actions(self):
        """Verify all supported PR actions."""
        supported_actions = ["opened", "synchronize", "reopened"]
        for action in supported_actions:
            assert should_process_event("pull_request", action) is True

    def test_supported_pr_review_comment_actions(self):
        """Verify all supported PR review comment actions."""
        assert should_process_event("pull_request_review_comment", "created") is True
