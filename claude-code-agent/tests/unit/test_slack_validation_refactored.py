"""TDD tests for Slack validate_response_format refactoring (Phase 4)."""

import pytest


class TestSlackValidateResponseFormat:
    """Test Slack validate_response_format is available in validation.py."""

    def test_validate_response_format_can_be_imported(self):
        """validate_response_format should be importable from slack.validation."""
        from api.webhooks.slack.validation import validate_response_format

        assert callable(validate_response_format)

    def test_validate_slack_format_valid(self):
        """Validate correct Slack message format passes."""
        from api.webhooks.slack.validation import validate_response_format

        valid_message = "This is a valid Slack message that is under 4000 characters."
        is_valid, error_msg = validate_response_format(valid_message, "slack")

        assert is_valid is True
        assert error_msg == ""

    def test_validate_slack_message_too_long(self):
        """Slack message over 4000 characters should fail."""
        from api.webhooks.slack.validation import validate_response_format

        long_message = "x" * 4001
        is_valid, error_msg = validate_response_format(long_message, "slack")

        assert is_valid is False
        assert "4000" in error_msg or "character" in error_msg.lower() or "limit" in error_msg.lower()

    def test_validate_slack_empty_message(self):
        """Empty Slack message should fail."""
        from api.webhooks.slack.validation import validate_response_format

        empty_message = ""
        is_valid, error_msg = validate_response_format(empty_message, "slack")

        assert is_valid is False
        assert "empty" in error_msg.lower()

    def test_validate_slack_whitespace_only_message(self):
        """Whitespace-only Slack message should fail."""
        from api.webhooks.slack.validation import validate_response_format

        whitespace_message = "   \n\t  "
        is_valid, error_msg = validate_response_format(whitespace_message, "slack")

        assert is_valid is False
        assert "empty" in error_msg.lower()
