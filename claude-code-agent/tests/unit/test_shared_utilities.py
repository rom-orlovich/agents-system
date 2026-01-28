"""
Tests for shared utilities - written first following TDD approach.

These utilities consolidate duplicated code for:
- Text extraction from various webhook payload formats
- Message truncation and formatting
"""

import pytest


# =============================================================================
# TEST: TextExtractor
# =============================================================================

class TestTextExtractor:
    """Tests for TextExtractor utility."""

    def test_extract_from_string(self):
        """Test extracting text from string."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract("Hello World")
        assert result == "Hello World"

    def test_extract_from_none_returns_default(self):
        """Test extracting from None returns default."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract(None)
        assert result == ""

        result = TextExtractor.extract(None, default="N/A")
        assert result == "N/A"

    def test_extract_from_empty_string(self):
        """Test extracting from empty string."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract("")
        assert result == ""

    def test_extract_from_list(self):
        """Test extracting text from list."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract(["Hello", "World"])
        assert result == "Hello World"

    def test_extract_from_empty_list(self):
        """Test extracting from empty list returns default."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract([])
        assert result == ""

    def test_extract_from_list_with_none_items(self):
        """Test extracting from list with None items."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract(["Hello", None, "World"])
        assert result == "Hello World"

    def test_extract_from_dict_with_text_key(self):
        """Test extracting from dict with 'text' key."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract({"text": "Hello World"})
        assert result == "Hello World"

    def test_extract_from_dict_with_body_key(self):
        """Test extracting from dict with 'body' key."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract({"body": "Hello World"})
        assert result == "Hello World"

    def test_extract_from_dict_with_content_key(self):
        """Test extracting from dict with 'content' key."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract({"content": "Hello World"})
        assert result == "Hello World"

    def test_extract_from_nested_dict(self):
        """Test extracting from nested dict."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract({"body": {"text": "Hello World"}})
        assert result == "Hello World"

    def test_extract_with_custom_keys(self):
        """Test extracting with custom keys to try."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract(
            {"message": "Hello World"},
            keys_to_try=("message", "text")
        )
        assert result == "Hello World"

    def test_extract_from_jira_adf_format(self):
        """Test extracting from Jira ADF format."""
        from domain.services.text_extraction import TextExtractor

        adf_content = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Hello "},
                        {"type": "text", "text": "World"},
                    ]
                }
            ]
        }
        result = TextExtractor.extract_jira_adf(adf_content)
        assert "Hello" in result
        assert "World" in result

    def test_extract_converts_other_types_to_string(self):
        """Test that other types are converted to string."""
        from domain.services.text_extraction import TextExtractor

        result = TextExtractor.extract(42)
        assert result == "42"

        result = TextExtractor.extract(3.14)
        assert result == "3.14"


# =============================================================================
# TEST: MessageFormatter
# =============================================================================

class TestMessageFormatter:
    """Tests for MessageFormatter utility."""

    def test_truncate_short_message(self):
        """Test truncation of short message (no change)."""
        from domain.services.message_formatting import MessageFormatter

        message = "Short message"
        result = MessageFormatter.truncate(message, max_length=100)
        assert result == message

    def test_truncate_long_message(self):
        """Test truncation of long message."""
        from domain.services.message_formatting import MessageFormatter

        message = "A" * 200
        result = MessageFormatter.truncate(message, max_length=100)

        assert len(result) <= 100 + len("\n\n... (truncated)")
        assert result.endswith("... (truncated)")

    def test_truncate_at_sentence_boundary(self):
        """Test truncation at sentence boundary."""
        from domain.services.message_formatting import MessageFormatter

        message = "First sentence. Second sentence. Third sentence is longer."
        result = MessageFormatter.truncate(message, max_length=35)

        # Should truncate at sentence boundary
        assert result.endswith("... (truncated)") or result.endswith(".")

    def test_truncate_at_newline_boundary(self):
        """Test truncation at newline boundary."""
        from domain.services.message_formatting import MessageFormatter

        message = "Line 1\nLine 2\nLine 3 is much longer than the others"
        result = MessageFormatter.truncate(message, max_length=20)

        assert "... (truncated)" in result or "\n" not in result[-20:]

    def test_truncate_with_custom_suffix(self):
        """Test truncation with custom suffix."""
        from domain.services.message_formatting import MessageFormatter

        message = "A" * 200
        result = MessageFormatter.truncate(message, max_length=100, suffix="...")

        assert result.endswith("...")

    def test_format_github_comment_success(self):
        """Test formatting GitHub comment for success."""
        from domain.services.message_formatting import MessageFormatter

        result = MessageFormatter.format_github_comment(
            message="Task completed successfully",
            success=True,
        )

        assert result.startswith("✅")
        assert "Task completed successfully" in result

    def test_format_github_comment_failure(self):
        """Test formatting GitHub comment for failure."""
        from domain.services.message_formatting import MessageFormatter

        result = MessageFormatter.format_github_comment(
            message="Task failed",
            success=False,
        )

        assert result.startswith("❌")
        assert "Task failed" in result

    def test_format_github_comment_with_cost(self):
        """Test formatting GitHub comment with cost."""
        from domain.services.message_formatting import MessageFormatter

        result = MessageFormatter.format_github_comment(
            message="Task completed",
            success=True,
            cost_usd=0.05,
        )

        assert "💰" in result or "$0.05" in result

    def test_format_github_comment_truncates_long_message(self):
        """Test that long messages are truncated."""
        from domain.services.message_formatting import MessageFormatter

        long_message = "A" * 10000
        result = MessageFormatter.format_github_comment(
            message=long_message,
            success=True,
        )

        assert len(result) < 10000

    def test_format_jira_comment_success(self):
        """Test formatting Jira comment for success."""
        from domain.services.message_formatting import MessageFormatter

        result = MessageFormatter.format_jira_comment(
            message="Task completed successfully",
            success=True,
        )

        assert "completed" in result.lower() or "✅" in result

    def test_format_jira_comment_with_pr_url(self):
        """Test formatting Jira comment with PR URL."""
        from domain.services.message_formatting import MessageFormatter

        result = MessageFormatter.format_jira_comment(
            message="Task completed",
            success=True,
            pr_url="https://github.com/owner/repo/pull/123",
        )

        assert "github.com" in result or "PR" in result or "pull" in result.lower()


# =============================================================================
# TEST: Command Extractor
# =============================================================================

class TestCommandExtractor:
    """Tests for command extraction from text."""

    def test_extract_command_basic(self):
        """Test extracting basic command."""
        from domain.services.command_extraction import extract_command

        result = extract_command("@agent review this code")

        assert result is not None
        command, content = result
        assert command == "review"
        assert "this code" in content

    def test_extract_command_with_alias(self):
        """Test extracting command with common aliases."""
        from domain.services.command_extraction import extract_command

        # @agent and /agent should both work
        result1 = extract_command("@agent help")
        result2 = extract_command("/agent help")

        assert result1 is not None
        assert result2 is not None

    def test_extract_command_case_insensitive(self):
        """Test command extraction is case insensitive."""
        from domain.services.command_extraction import extract_command

        result1 = extract_command("@agent REVIEW this code")
        result2 = extract_command("@AGENT review this code")

        assert result1 is not None
        assert result2 is not None

    def test_extract_command_no_command(self):
        """Test extraction when no command present."""
        from domain.services.command_extraction import extract_command

        result = extract_command("Just a regular comment")

        assert result is None

    def test_extract_command_in_middle_of_text(self):
        """Test extracting command from middle of text."""
        from domain.services.command_extraction import extract_command

        result = extract_command("Hello! @agent review Please check this")

        assert result is not None
        command, _ = result
        assert command == "review"

    def test_extract_command_with_multiline_content(self):
        """Test extracting command with multiline content."""
        from domain.services.command_extraction import extract_command

        result = extract_command("@agent implement\n\nPlease implement this feature:\n- Item 1\n- Item 2")

        assert result is not None
        command, content = result
        assert command == "implement"
        assert "Item 1" in content


# =============================================================================
# TEST: Bot Detection
# =============================================================================

class TestBotDetection:
    """Tests for bot detection."""

    def test_detect_github_bot(self):
        """Test detecting GitHub bot."""
        from domain.services.bot_detection import is_bot

        assert is_bot(login="github-actions[bot]", user_type="Bot") is True
        assert is_bot(login="dependabot[bot]", user_type="Bot") is True

    def test_detect_bot_by_type(self):
        """Test detecting bot by user type."""
        from domain.services.bot_detection import is_bot

        assert is_bot(login="some-user", user_type="Bot") is True

    def test_detect_bot_by_login_suffix(self):
        """Test detecting bot by login suffix."""
        from domain.services.bot_detection import is_bot

        assert is_bot(login="my-bot[bot]", user_type="User") is True

    def test_regular_user_not_bot(self):
        """Test that regular users are not detected as bots."""
        from domain.services.bot_detection import is_bot

        assert is_bot(login="john-doe", user_type="User") is False

    def test_bot_detection_case_insensitive(self):
        """Test bot detection is case insensitive."""
        from domain.services.bot_detection import is_bot

        assert is_bot(login="MyBot[BOT]", user_type="user") is True
