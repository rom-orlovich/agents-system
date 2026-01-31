from agent_engine.core.cli.sanitization import (
    contains_sensitive_data,
    sanitize_sensitive_content,
)


class TestSanitization:
    def test_sanitize_github_token(self) -> None:
        content = "GITHUB_TOKEN=ghp_abc123xyz"
        sanitized = sanitize_sensitive_content(content)
        assert "ghp_abc123xyz" not in sanitized
        assert "***REDACTED***" in sanitized

    def test_sanitize_jira_token(self) -> None:
        content = "JIRA_API_TOKEN=secret123"
        sanitized = sanitize_sensitive_content(content)
        assert "secret123" not in sanitized
        assert "***REDACTED***" in sanitized

    def test_sanitize_slack_token(self) -> None:
        content = "SLACK_BOT_TOKEN=xoxb-12345"
        sanitized = sanitize_sensitive_content(content)
        assert "xoxb-12345" not in sanitized
        assert "***REDACTED***" in sanitized

    def test_sanitize_authorization_header(self) -> None:
        content = "Authorization: Bearer sk-1234567890"
        sanitized = sanitize_sensitive_content(content)
        assert "sk-1234567890" not in sanitized
        assert "***REDACTED***" in sanitized

    def test_sanitize_basic_auth(self) -> None:
        content = "Authorization: Basic dXNlcjpwYXNz"
        sanitized = sanitize_sensitive_content(content)
        assert "dXNlcjpwYXNz" not in sanitized

    def test_sanitize_password_field(self) -> None:
        content = "password=mysecretpassword"
        sanitized = sanitize_sensitive_content(content)
        assert "mysecretpassword" not in sanitized

    def test_sanitize_preserves_normal_content(self) -> None:
        content = "Hello world, this is normal text"
        sanitized = sanitize_sensitive_content(content)
        assert sanitized == content

    def test_sanitize_handles_empty_content(self) -> None:
        assert sanitize_sensitive_content("") == ""
        assert sanitize_sensitive_content(None) == ""

    def test_sanitize_handles_list_input(self) -> None:
        content = ["line1", "GITHUB_TOKEN=secret", "line3"]
        sanitized = sanitize_sensitive_content(content)
        assert "secret" not in sanitized
        assert "line1" in sanitized
        assert "line3" in sanitized


class TestContainsSensitiveData:
    def test_contains_github_token(self) -> None:
        assert contains_sensitive_data("GITHUB_TOKEN=abc") is True

    def test_contains_password(self) -> None:
        assert contains_sensitive_data("password: secret123") is True

    def test_contains_token(self) -> None:
        assert contains_sensitive_data("token=abc123") is True

    def test_contains_authorization(self) -> None:
        assert contains_sensitive_data("Authorization: Bearer xxx") is True

    def test_normal_content_not_sensitive(self) -> None:
        assert contains_sensitive_data("hello world") is False

    def test_empty_content_not_sensitive(self) -> None:
        assert contains_sensitive_data("") is False
        assert contains_sensitive_data(None) is False
