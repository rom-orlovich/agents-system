import pytest
from pydantic import ValidationError
from api.webhooks.github.models import (
    GitHubUser,
    GitHubRepository,
    GitHubIssue,
    GitHubComment,
    GitHubPullRequest,
    GitHubIssueCommentPayload,
    GitHubIssuesPayload,
    GitHubPullRequestPayload,
    GitHubWebhookPayload,
)


class TestGitHubUser:
    def test_valid_user(self):
        user_data = {"login": "testuser", "id": 123, "type": "User"}
        user = GitHubUser(**user_data)
        assert user.login == "testuser"
        assert user.id == 123
        assert user.type == "User"

    def test_user_missing_required_fields(self):
        with pytest.raises(ValidationError) as exc_info:
            GitHubUser(login="testuser")
        assert "id" in str(exc_info.value)


class TestGitHubRepository:
    def test_valid_repository(self):
        user_data = {"login": "owner", "id": 1, "type": "User"}
        repo_data = {
            "id": 456,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "owner": user_data,
            "private": False,
        }
        repo = GitHubRepository(**repo_data)
        assert repo.name == "test-repo"
        assert repo.full_name == "owner/test-repo"
        assert repo.owner.login == "owner"
        assert repo.private is False

    def test_repository_missing_owner(self):
        repo_data = {
            "id": 456,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "private": False,
        }
        with pytest.raises(ValidationError) as exc_info:
            GitHubRepository(**repo_data)
        assert "owner" in str(exc_info.value)


class TestGitHubIssue:
    def test_valid_issue(self):
        user_data = {"login": "testuser", "id": 123, "type": "User"}
        issue_data = {
            "id": 789,
            "number": 42,
            "title": "Test Issue",
            "body": "This is a test issue",
            "state": "open",
            "user": user_data,
        }
        issue = GitHubIssue(**issue_data)
        assert issue.number == 42
        assert issue.title == "Test Issue"
        assert issue.body == "This is a test issue"
        assert issue.state == "open"

    def test_issue_without_body(self):
        user_data = {"login": "testuser", "id": 123, "type": "User"}
        issue_data = {
            "id": 789,
            "number": 42,
            "title": "Test Issue",
            "state": "open",
            "user": user_data,
        }
        issue = GitHubIssue(**issue_data)
        assert issue.body is None

    def test_issue_with_pull_request(self):
        user_data = {"login": "testuser", "id": 123, "type": "User"}
        issue_data = {
            "id": 789,
            "number": 42,
            "title": "Test Issue",
            "state": "open",
            "user": user_data,
            "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/42"},
        }
        issue = GitHubIssue(**issue_data)
        assert issue.pull_request is not None


class TestGitHubComment:
    def test_valid_comment(self):
        user_data = {"login": "testuser", "id": 123, "type": "User"}
        comment_data = {
            "id": 999,
            "body": "@agent review this PR",
            "user": user_data,
            "created_at": "2024-01-01T00:00:00Z",
        }
        comment = GitHubComment(**comment_data)
        assert comment.id == 999
        assert comment.body == "@agent review this PR"
        assert comment.user.login == "testuser"

    def test_comment_missing_created_at(self):
        user_data = {"login": "testuser", "id": 123, "type": "User"}
        comment_data = {"id": 999, "body": "@agent review this PR", "user": user_data}
        with pytest.raises(ValidationError) as exc_info:
            GitHubComment(**comment_data)
        assert "created_at" in str(exc_info.value)


class TestGitHubPullRequest:
    def test_valid_pull_request(self):
        user_data = {"login": "testuser", "id": 123, "type": "User"}
        pr_data = {
            "id": 888,
            "number": 10,
            "title": "Test PR",
            "body": "This is a test PR",
            "state": "open",
            "user": user_data,
        }
        pr = GitHubPullRequest(**pr_data)
        assert pr.number == 10
        assert pr.title == "Test PR"
        assert pr.body == "This is a test PR"
        assert pr.state == "open"

    def test_pull_request_without_body(self):
        user_data = {"login": "testuser", "id": 123, "type": "User"}
        pr_data = {
            "id": 888,
            "number": 10,
            "title": "Test PR",
            "state": "open",
            "user": user_data,
        }
        pr = GitHubPullRequest(**pr_data)
        assert pr.body is None


class TestGitHubIssueCommentPayload:
    def test_valid_issue_comment_payload(self):
        payload_data = {
            "action": "created",
            "issue": {
                "id": 789,
                "number": 42,
                "title": "Test Issue",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "comment": {
                "id": 999,
                "body": "@agent review",
                "user": {"login": "commenter", "id": 456, "type": "User"},
                "created_at": "2024-01-01T00:00:00Z",
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "commenter", "id": 456, "type": "User"},
        }
        payload = GitHubIssueCommentPayload(**payload_data)
        assert payload.action == "created"
        assert payload.issue.number == 42
        assert payload.comment.id == 999
        assert payload.repository.name == "test-repo"
        assert payload.sender.login == "commenter"

    def test_issue_comment_invalid_action(self):
        payload_data = {
            "action": "invalid_action",
            "issue": {
                "id": 789,
                "number": 42,
                "title": "Test Issue",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "comment": {
                "id": 999,
                "body": "@agent review",
                "user": {"login": "commenter", "id": 456, "type": "User"},
                "created_at": "2024-01-01T00:00:00Z",
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "commenter", "id": 456, "type": "User"},
        }
        with pytest.raises(ValidationError) as exc_info:
            GitHubIssueCommentPayload(**payload_data)
        assert "action" in str(exc_info.value)

    def test_issue_comment_text_extraction(self):
        payload_data = {
            "action": "created",
            "issue": {
                "id": 789,
                "number": 42,
                "title": "Test Issue",
                "body": "Issue body text",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "comment": {
                "id": 999,
                "body": "@agent review this code",
                "user": {"login": "commenter", "id": 456, "type": "User"},
                "created_at": "2024-01-01T00:00:00Z",
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "commenter", "id": 456, "type": "User"},
        }
        payload = GitHubIssueCommentPayload(**payload_data)
        text = payload.extract_text()
        assert text == "@agent review this code"


class TestGitHubIssuesPayload:
    def test_valid_issues_payload(self):
        payload_data = {
            "action": "opened",
            "issue": {
                "id": 789,
                "number": 42,
                "title": "New Issue",
                "body": "This is a new issue",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "testuser", "id": 123, "type": "User"},
        }
        payload = GitHubIssuesPayload(**payload_data)
        assert payload.action == "opened"
        assert payload.issue.number == 42
        assert payload.issue.title == "New Issue"

    def test_issues_invalid_action(self):
        payload_data = {
            "action": "unknown",
            "issue": {
                "id": 789,
                "number": 42,
                "title": "New Issue",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "testuser", "id": 123, "type": "User"},
        }
        with pytest.raises(ValidationError) as exc_info:
            GitHubIssuesPayload(**payload_data)
        assert "action" in str(exc_info.value)

    def test_issues_text_extraction(self):
        payload_data = {
            "action": "opened",
            "issue": {
                "id": 789,
                "number": 42,
                "title": "Issue Title",
                "body": "Issue body text with details",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "testuser", "id": 123, "type": "User"},
        }
        payload = GitHubIssuesPayload(**payload_data)
        text = payload.extract_text()
        assert "Issue Title" in text
        assert "Issue body text with details" in text


class TestGitHubPullRequestPayload:
    def test_valid_pull_request_payload(self):
        payload_data = {
            "action": "opened",
            "pull_request": {
                "id": 888,
                "number": 10,
                "title": "Test PR",
                "body": "This is a test PR",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "testuser", "id": 123, "type": "User"},
        }
        payload = GitHubPullRequestPayload(**payload_data)
        assert payload.action == "opened"
        assert payload.pull_request.number == 10
        assert payload.pull_request.title == "Test PR"

    def test_pull_request_invalid_action(self):
        payload_data = {
            "action": "invalid",
            "pull_request": {
                "id": 888,
                "number": 10,
                "title": "Test PR",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "testuser", "id": 123, "type": "User"},
        }
        with pytest.raises(ValidationError) as exc_info:
            GitHubPullRequestPayload(**payload_data)
        assert "action" in str(exc_info.value)

    def test_pull_request_text_extraction(self):
        payload_data = {
            "action": "opened",
            "pull_request": {
                "id": 888,
                "number": 10,
                "title": "Add new feature",
                "body": "PR description with context",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "testuser", "id": 123, "type": "User"},
        }
        payload = GitHubPullRequestPayload(**payload_data)
        text = payload.extract_text()
        assert "Add new feature" in text
        assert "PR description with context" in text


class TestGitHubWebhookPayload:
    def test_discriminated_union_issue_comment(self):
        payload_data = {
            "action": "created",
            "issue": {
                "id": 789,
                "number": 42,
                "title": "Test Issue",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "comment": {
                "id": 999,
                "body": "@agent review",
                "user": {"login": "commenter", "id": 456, "type": "User"},
                "created_at": "2024-01-01T00:00:00Z",
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "commenter", "id": 456, "type": "User"},
        }
        payload = GitHubWebhookPayload.parse_obj(payload_data)
        assert isinstance(payload, GitHubIssueCommentPayload)
        assert payload.comment.body == "@agent review"

    def test_discriminated_union_issues(self):
        payload_data = {
            "action": "opened",
            "issue": {
                "id": 789,
                "number": 42,
                "title": "New Issue",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "testuser", "id": 123, "type": "User"},
        }
        payload = GitHubWebhookPayload.parse_obj(payload_data)
        assert isinstance(payload, GitHubIssuesPayload)
        assert payload.issue.title == "New Issue"

    def test_discriminated_union_pull_request(self):
        payload_data = {
            "action": "opened",
            "pull_request": {
                "id": 888,
                "number": 10,
                "title": "Test PR",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "testuser", "id": 123, "type": "User"},
        }
        payload = GitHubWebhookPayload.parse_obj(payload_data)
        assert isinstance(payload, GitHubPullRequestPayload)
        assert payload.pull_request.title == "Test PR"

    def test_text_extraction_priority_comment_over_pr(self):
        payload_data = {
            "action": "created",
            "issue": {
                "id": 789,
                "number": 42,
                "title": "Test Issue",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
                "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/42"},
            },
            "comment": {
                "id": 999,
                "body": "Comment text here",
                "user": {"login": "commenter", "id": 456, "type": "User"},
                "created_at": "2024-01-01T00:00:00Z",
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "commenter", "id": 456, "type": "User"},
        }
        payload = GitHubWebhookPayload.parse_obj(payload_data)
        text = payload.extract_text()
        assert text == "Comment text here"

    def test_text_extraction_fallback_to_issue_body(self):
        payload_data = {
            "action": "opened",
            "issue": {
                "id": 789,
                "number": 42,
                "title": "Issue Title",
                "body": "Issue body",
                "state": "open",
                "user": {"login": "testuser", "id": 123, "type": "User"},
            },
            "repository": {
                "id": 111,
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "owner": {"login": "owner", "id": 1, "type": "User"},
                "private": False,
            },
            "sender": {"login": "testuser", "id": 123, "type": "User"},
        }
        payload = GitHubWebhookPayload.parse_obj(payload_data)
        text = payload.extract_text()
        assert "Issue Title" in text and "Issue body" in text
