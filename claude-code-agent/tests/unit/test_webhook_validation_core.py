"""Unit tests for core webhook validation utilities."""

import pytest
from core.webhook_validation import (
    WebhookValidationResult,
    extract_command,
    validate_command,
    VALID_COMMANDS,
)


class TestWebhookValidationResult:
    """Test WebhookValidationResult model."""
    
    def test_success_creates_valid_result(self):
        """Success factory method creates valid result."""
        result = WebhookValidationResult.success()
        assert result.is_valid is True
        assert result.error_message == ""
    
    def test_failure_creates_invalid_result(self):
        """Failure factory method creates invalid result with error message."""
        error_msg = "Test error message"
        result = WebhookValidationResult.failure(error_msg)
        assert result.is_valid is False
        assert result.error_message == error_msg
    
    def test_result_can_be_created_directly(self):
        """Result can be created directly with is_valid and error_message."""
        result = WebhookValidationResult(is_valid=True, error_message="")
        assert result.is_valid is True
        
        result = WebhookValidationResult(is_valid=False, error_message="Custom error")
        assert result.is_valid is False
        assert result.error_message == "Custom error"


class TestExtractCommand:
    """Test extract_command utility function."""
    
    def test_extracts_command_after_agent(self):
        """Extracts command that follows @agent."""
        text = "@agent review this PR"
        command = extract_command(text)
        assert command == "review"
    
    def test_extracts_command_case_insensitive(self):
        """Extracts command case-insensitively."""
        text = "@AGENT REVIEW this PR"
        command = extract_command(text)
        assert command == "review"
    
    def test_extracts_first_command_if_multiple(self):
        """Extracts first command if multiple @agent mentions."""
        text = "@agent review and @agent fix"
        command = extract_command(text)
        assert command == "review"
    
    def test_handles_command_with_numbers(self):
        """Handles commands with alphanumeric characters."""
        text = "@agent fix123"
        command = extract_command(text)
        assert command == "fix123"
    
    def test_returns_none_if_no_agent_prefix(self):
        """Returns None if no @agent prefix found."""
        text = "Just a regular comment"
        command = extract_command(text)
        assert command is None
    
    def test_returns_none_if_no_command_after_agent(self):
        """Returns None if @agent has no command after it."""
        text = "@agent"
        command = extract_command(text)
        assert command is None
    
    def test_handles_whitespace_variations(self):
        """Handles various whitespace patterns."""
        text = "@agent  review"
        command = extract_command(text)
        assert command == "review"
        
        text = "@agent\treview"
        command = extract_command(text)
        assert command == "review"
    
    def test_handles_command_at_end_of_text(self):
        """Handles command at end of text."""
        text = "Please @agent review"
        command = extract_command(text)
        assert command == "review"
    
    def test_handles_command_in_middle_of_text(self):
        """Handles command in middle of text."""
        text = "Hey @agent review this and let me know"
        command = extract_command(text)
        assert command == "review"


class TestValidateCommand:
    """Test validate_command utility function."""
    
    def test_validates_all_valid_commands(self):
        """All valid commands pass validation."""
        for command in VALID_COMMANDS:
            is_valid, error_msg = validate_command(command)
            assert is_valid, f"Command '{command}' should be valid but got: {error_msg}"
            assert error_msg == ""
    
    def test_rejects_invalid_command(self):
        """Invalid commands are rejected."""
        is_valid, error_msg = validate_command("invalidcommand")
        assert not is_valid
        assert "invalid command" in error_msg.lower()
        assert "invalidcommand" in error_msg
    
    def test_rejects_none_command(self):
        """None command is rejected."""
        is_valid, error_msg = validate_command(None)
        assert not is_valid
        assert "@agent" in error_msg.lower()
    
    def test_rejects_empty_string_command(self):
        """Empty string command is rejected."""
        is_valid, error_msg = validate_command("")
        assert not is_valid
    
    def test_case_sensitive_command_validation(self):
        """Command validation is case-sensitive (commands are lowercase)."""
        is_valid, _ = validate_command("Review")
        assert not is_valid
        
        is_valid, _ = validate_command("review")
        assert is_valid
    
    def test_validates_command_with_whitespace(self):
        """Commands with whitespace are handled correctly."""
        is_valid, _ = validate_command(" review ")
        assert not is_valid


class TestValidCommandsConstant:
    """Test VALID_COMMANDS constant."""
    
    def test_contains_all_expected_commands(self):
        """VALID_COMMANDS contains all expected command names."""
        expected_commands = {
            "analyze", "plan", "fix", "review", 
            "approve", "reject", "improve", "help", "discover"
        }
        assert VALID_COMMANDS == expected_commands
    
    def test_is_a_set(self):
        """VALID_COMMANDS is a set for O(1) lookup."""
        assert isinstance(VALID_COMMANDS, set)
    
    def test_all_commands_are_lowercase(self):
        """All commands in VALID_COMMANDS are lowercase."""
        for command in VALID_COMMANDS:
            assert command.islower(), f"Command '{command}' should be lowercase"
