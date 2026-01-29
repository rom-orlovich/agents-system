"""
Tests for domain exceptions - written first following TDD approach.
"""

import pytest


class TestWebhookError:
    """Tests for WebhookError base class."""

    def test_basic_error(self):
        """Test creating basic webhook error."""
        from domain.exceptions import WebhookError

        error = WebhookError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.recoverable is True
        assert error.context == {}

    def test_error_with_context(self):
        """Test error with context."""
        from domain.exceptions import WebhookError

        error = WebhookError(
            "Something went wrong",
            context={"task_id": "123", "source": "github"}
        )

        assert error.context["task_id"] == "123"
        assert error.context["source"] == "github"

    def test_non_recoverable_error(self):
        """Test non-recoverable error."""
        from domain.exceptions import WebhookError

        error = WebhookError("Fatal error", recoverable=False)

        assert error.recoverable is False

    def test_to_dict(self):
        """Test converting error to dictionary."""
        from domain.exceptions import WebhookError

        error = WebhookError(
            "Test error",
            context={"foo": "bar"},
            recoverable=False,
        )

        result = error.to_dict()

        assert result["error"] == "Test error"
        assert result["error_type"] == "WebhookError"
        assert result["recoverable"] is False
        assert result["foo"] == "bar"


class TestWebhookValidationError:
    """Tests for WebhookValidationError."""

    def test_basic_validation_error(self):
        """Test creating basic validation error."""
        from domain.exceptions import WebhookValidationError

        error = WebhookValidationError("Invalid payload")

        assert error.message == "Invalid payload"
        assert error.recoverable is False  # Validation errors not recoverable

    def test_validation_error_with_field(self):
        """Test validation error with field info."""
        from domain.exceptions import WebhookValidationError

        error = WebhookValidationError(
            "Field required",
            field="repository",
            expected="dict",
            actual="None",
        )

        assert error.field == "repository"
        assert error.expected == "dict"
        assert error.actual == "None"
        assert error.context["field"] == "repository"


class TestWebhookAuthenticationError:
    """Tests for WebhookAuthenticationError."""

    def test_basic_auth_error(self):
        """Test creating basic auth error."""
        from domain.exceptions import WebhookAuthenticationError

        error = WebhookAuthenticationError("Invalid signature")

        assert error.message == "Invalid signature"
        assert error.recoverable is False  # Auth errors not recoverable

    def test_auth_error_with_source(self):
        """Test auth error with source."""
        from domain.exceptions import WebhookAuthenticationError

        error = WebhookAuthenticationError(
            "Secret not configured",
            source="github",
        )

        assert error.source == "github"
        assert error.context["source"] == "github"


class TestTaskCreationError:
    """Tests for TaskCreationError."""

    def test_basic_creation_error(self):
        """Test creating basic task creation error."""
        from domain.exceptions import TaskCreationError

        error = TaskCreationError("Failed to create task")

        assert error.message == "Failed to create task"
        assert error.recoverable is True  # Task creation can be retried

    def test_creation_error_with_task_info(self):
        """Test creation error with task info."""
        from domain.exceptions import TaskCreationError

        error = TaskCreationError(
            "Database error",
            task_id="task-123",
            webhook_source="github",
            command="review",
        )

        assert error.task_id == "task-123"
        assert error.webhook_source == "github"
        assert error.command == "review"


class TestExternalServiceError:
    """Tests for ExternalServiceError."""

    def test_basic_service_error(self):
        """Test creating basic service error."""
        from domain.exceptions import ExternalServiceError

        error = ExternalServiceError("API call failed", service="github")

        assert error.service == "github"
        assert error.status_code is None

    def test_service_error_with_status_code(self):
        """Test service error with status code."""
        from domain.exceptions import ExternalServiceError

        error = ExternalServiceError(
            "Unauthorized",
            service="jira",
            status_code=401,
        )

        assert error.status_code == 401
        assert error.context["status_code"] == 401

    def test_rate_limit_is_recoverable(self):
        """Test that rate limit errors are recoverable."""
        from domain.exceptions import ExternalServiceError

        error = ExternalServiceError(
            "Rate limit",
            service="github",
            status_code=429,
        )

        assert error.recoverable is True

    def test_server_error_is_recoverable(self):
        """Test that server errors are recoverable."""
        from domain.exceptions import ExternalServiceError

        for code in [502, 503, 504]:
            error = ExternalServiceError(
                "Server error",
                service="github",
                status_code=code,
            )
            assert error.recoverable is True

    def test_client_error_not_recoverable(self):
        """Test that client errors are not recoverable."""
        from domain.exceptions import ExternalServiceError

        error = ExternalServiceError(
            "Not found",
            service="github",
            status_code=404,
        )

        assert error.recoverable is False


class TestTokenNotConfiguredError:
    """Tests for TokenNotConfiguredError."""

    def test_basic_token_error(self):
        """Test creating basic token error."""
        from domain.exceptions import TokenNotConfiguredError

        error = TokenNotConfiguredError("GITHUB_TOKEN")

        assert "GITHUB_TOKEN" in str(error)
        assert error.token_name == "GITHUB_TOKEN"
        assert error.recoverable is False

    def test_token_error_with_env_var(self):
        """Test token error with env var suggestion."""
        from domain.exceptions import TokenNotConfiguredError

        error = TokenNotConfiguredError(
            "GitHub API Token",
            env_var="GITHUB_TOKEN",
        )

        assert "GITHUB_TOKEN" in str(error)
        assert error.env_var == "GITHUB_TOKEN"


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_basic_rate_limit(self):
        """Test creating basic rate limit error."""
        from domain.exceptions import RateLimitError

        error = RateLimitError("github")

        assert error.service == "github"
        assert error.status_code == 429
        assert error.recoverable is True

    def test_rate_limit_with_retry_after(self):
        """Test rate limit with retry-after."""
        from domain.exceptions import RateLimitError

        error = RateLimitError("github", retry_after=60)

        assert error.retry_after == 60
        assert "60 seconds" in str(error)


class TestCommandMatchError:
    """Tests for CommandMatchError."""

    def test_basic_command_error(self):
        """Test creating basic command match error."""
        from domain.exceptions import CommandMatchError

        error = CommandMatchError("Command not found")

        assert error.message == "Command not found"
        assert error.recoverable is False

    def test_command_error_with_details(self):
        """Test command error with details."""
        from domain.exceptions import CommandMatchError

        error = CommandMatchError(
            "Unknown command",
            command="invalid",
            available_commands=["review", "approve", "reject"],
        )

        assert error.command == "invalid"
        assert "review" in error.available_commands


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    def test_all_inherit_from_webhook_error(self):
        """Test all exceptions inherit from WebhookError."""
        from domain.exceptions import (
            WebhookError,
            WebhookValidationError,
            WebhookAuthenticationError,
            TaskCreationError,
            ExternalServiceError,
            TokenNotConfiguredError,
            RateLimitError,
            CommandMatchError,
        )

        assert issubclass(WebhookValidationError, WebhookError)
        assert issubclass(WebhookAuthenticationError, WebhookError)
        assert issubclass(TaskCreationError, WebhookError)
        assert issubclass(ExternalServiceError, WebhookError)
        assert issubclass(TokenNotConfiguredError, WebhookError)
        assert issubclass(RateLimitError, ExternalServiceError)
        assert issubclass(CommandMatchError, WebhookError)

    def test_can_catch_all_with_webhook_error(self):
        """Test catching all webhook errors."""
        from domain.exceptions import (
            WebhookError,
            WebhookValidationError,
        )

        try:
            raise WebhookValidationError("Test")
        except WebhookError as e:
            assert e.message == "Test"
