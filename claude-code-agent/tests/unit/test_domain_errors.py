import pytest
from api.webhooks.github.errors import (
    GitHubErrorContext,
    GitHubValidationError,
    GitHubProcessingError,
    GitHubResponseError,
    GitHubSignatureError,
)
from api.webhooks.jira.errors import (
    JiraErrorContext,
    JiraValidationError,
    JiraProcessingError,
    JiraResponseError,
)
from api.webhooks.slack.errors import (
    SlackErrorContext,
    SlackValidationError,
    SlackProcessingError,
    SlackResponseError,
)


class TestGitHubErrorContext:
    def test_empty_context(self):
        context = GitHubErrorContext()
        assert context.repo is None
        assert context.issue_number is None
        assert context.pr_number is None
        assert context.comment_id is None
        assert context.task_id is None
        assert context.event_type is None

    def test_context_with_all_fields(self):
        context = GitHubErrorContext(
            repo="owner/repo",
            issue_number=42,
            pr_number=10,
            comment_id=999,
            task_id="task-123",
            event_type="issue_comment.created",
        )
        assert context.repo == "owner/repo"
        assert context.issue_number == 42
        assert context.pr_number == 10
        assert context.comment_id == 999
        assert context.task_id == "task-123"
        assert context.event_type == "issue_comment.created"

    def test_context_partial_fields(self):
        context = GitHubErrorContext(repo="owner/repo", issue_number=42)
        assert context.repo == "owner/repo"
        assert context.issue_number == 42
        assert context.pr_number is None


class TestGitHubErrors:
    def test_validation_error_with_context(self):
        context = GitHubErrorContext(repo="owner/repo", issue_number=42)
        error = GitHubValidationError("Invalid payload", context=context)
        assert str(error) == "Invalid payload"
        assert error.context.repo == "owner/repo"
        assert error.context.issue_number == 42

    def test_validation_error_without_context(self):
        error = GitHubValidationError("Invalid payload")
        assert str(error) == "Invalid payload"
        assert error.context is not None
        assert error.context.repo is None

    def test_processing_error_with_context(self):
        context = GitHubErrorContext(task_id="task-123", event_type="issues.opened")
        error = GitHubProcessingError("Processing failed", context=context)
        assert str(error) == "Processing failed"
        assert error.context.task_id == "task-123"
        assert error.context.event_type == "issues.opened"

    def test_response_error_with_context(self):
        context = GitHubErrorContext(pr_number=10, repo="owner/repo")
        error = GitHubResponseError("Response failed", context=context)
        assert str(error) == "Response failed"
        assert error.context.pr_number == 10
        assert error.context.repo == "owner/repo"

    def test_signature_error_with_context(self):
        context = GitHubErrorContext(event_type="issue_comment.created")
        error = GitHubSignatureError("Invalid signature", context=context)
        assert str(error) == "Invalid signature"
        assert error.context.event_type == "issue_comment.created"


class TestJiraErrorContext:
    def test_empty_context(self):
        context = JiraErrorContext()
        assert context.issue_key is None
        assert context.comment_id is None
        assert context.task_id is None
        assert context.event_type is None
        assert context.project_key is None

    def test_context_with_all_fields(self):
        context = JiraErrorContext(
            issue_key="TEST-123",
            comment_id="10200",
            task_id="task-456",
            event_type="jira:issue_created",
            project_key="TEST",
        )
        assert context.issue_key == "TEST-123"
        assert context.comment_id == "10200"
        assert context.task_id == "task-456"
        assert context.event_type == "jira:issue_created"
        assert context.project_key == "TEST"

    def test_context_partial_fields(self):
        context = JiraErrorContext(issue_key="TEST-123", project_key="TEST")
        assert context.issue_key == "TEST-123"
        assert context.project_key == "TEST"
        assert context.comment_id is None


class TestJiraErrors:
    def test_validation_error_with_context(self):
        context = JiraErrorContext(issue_key="TEST-123", event_type="jira:issue_created")
        error = JiraValidationError("Invalid payload", context=context)
        assert str(error) == "Invalid payload"
        assert error.context.issue_key == "TEST-123"
        assert error.context.event_type == "jira:issue_created"

    def test_validation_error_without_context(self):
        error = JiraValidationError("Invalid payload")
        assert str(error) == "Invalid payload"
        assert error.context is not None
        assert error.context.issue_key is None

    def test_processing_error_with_context(self):
        context = JiraErrorContext(task_id="task-456", issue_key="TEST-123")
        error = JiraProcessingError("Processing failed", context=context)
        assert str(error) == "Processing failed"
        assert error.context.task_id == "task-456"
        assert error.context.issue_key == "TEST-123"

    def test_response_error_with_context(self):
        context = JiraErrorContext(issue_key="TEST-123", comment_id="10200")
        error = JiraResponseError("Response failed", context=context)
        assert str(error) == "Response failed"
        assert error.context.issue_key == "TEST-123"
        assert error.context.comment_id == "10200"


class TestSlackErrorContext:
    def test_empty_context(self):
        context = SlackErrorContext()
        assert context.channel_id is None
        assert context.user_id is None
        assert context.task_id is None
        assert context.event_type is None
        assert context.team_id is None

    def test_context_with_all_fields(self):
        context = SlackErrorContext(
            channel_id="C123ABC",
            user_id="U123ABC",
            task_id="task-789",
            event_type="app_mention",
            team_id="T123ABC",
        )
        assert context.channel_id == "C123ABC"
        assert context.user_id == "U123ABC"
        assert context.task_id == "task-789"
        assert context.event_type == "app_mention"
        assert context.team_id == "T123ABC"

    def test_context_partial_fields(self):
        context = SlackErrorContext(channel_id="C123ABC", user_id="U123ABC")
        assert context.channel_id == "C123ABC"
        assert context.user_id == "U123ABC"
        assert context.team_id is None


class TestSlackErrors:
    def test_validation_error_with_context(self):
        context = SlackErrorContext(channel_id="C123ABC", event_type="app_mention")
        error = SlackValidationError("Invalid payload", context=context)
        assert str(error) == "Invalid payload"
        assert error.context.channel_id == "C123ABC"
        assert error.context.event_type == "app_mention"

    def test_validation_error_without_context(self):
        error = SlackValidationError("Invalid payload")
        assert str(error) == "Invalid payload"
        assert error.context is not None
        assert error.context.channel_id is None

    def test_processing_error_with_context(self):
        context = SlackErrorContext(task_id="task-789", channel_id="C123ABC")
        error = SlackProcessingError("Processing failed", context=context)
        assert str(error) == "Processing failed"
        assert error.context.task_id == "task-789"
        assert error.context.channel_id == "C123ABC"

    def test_response_error_with_context(self):
        context = SlackErrorContext(channel_id="C123ABC", user_id="U123ABC")
        error = SlackResponseError("Response failed", context=context)
        assert str(error) == "Response failed"
        assert error.context.channel_id == "C123ABC"
        assert error.context.user_id == "U123ABC"


class TestErrorContextSerialization:
    def test_github_context_dict(self):
        context = GitHubErrorContext(repo="owner/repo", issue_number=42, task_id="task-123")
        context_dict = context.__dict__
        assert context_dict["repo"] == "owner/repo"
        assert context_dict["issue_number"] == 42
        assert context_dict["task_id"] == "task-123"

    def test_jira_context_dict(self):
        context = JiraErrorContext(issue_key="TEST-123", project_key="TEST")
        context_dict = context.__dict__
        assert context_dict["issue_key"] == "TEST-123"
        assert context_dict["project_key"] == "TEST"

    def test_slack_context_dict(self):
        context = SlackErrorContext(channel_id="C123ABC", team_id="T123ABC")
        context_dict = context.__dict__
        assert context_dict["channel_id"] == "C123ABC"
        assert context_dict["team_id"] == "T123ABC"
