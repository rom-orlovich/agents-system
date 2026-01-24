"""Unit tests for command parser."""

import pytest
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.commands.parser import CommandParser
from shared.commands.loader import CommandLoader
from shared.enums import Platform, CommandType


class TestCommandParser:
    """Test command parsing functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return CommandParser()
    
    @pytest.fixture
    def loader(self):
        """Create loader instance."""
        return CommandLoader()
    
    # =========================================================================
    # Basic Parsing Tests
    # =========================================================================
    
    def test_parse_approve_command(self, parser):
        """Test parsing approve command."""
        result = parser.parse(
            text="@agent approve",
            platform=Platform.GITHUB,
            context={"pr_number": 123}
        )
        
        assert result is not None
        assert result.command_name == "approve"
        assert result.command_type == CommandType.APPROVE
    
    def test_parse_approve_alias(self, parser):
        """Test parsing approve with alias."""
        result = parser.parse(
            text="@agent lgtm",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "approve"
    
    def test_parse_reject_with_reason(self, parser):
        """Test parsing reject with reason."""
        result = parser.parse(
            text="@agent reject too risky",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "reject"
        assert result.args == ["too risky"]
    
    def test_parse_help_command(self, parser):
        """Test parsing help command."""
        result = parser.parse(
            text="@agent help",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "help"
    
    def test_parse_help_with_specific_command(self, parser):
        """Test parsing help with specific command."""
        result = parser.parse(
            text="@agent help approve",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "help"
        assert result.args == ["approve"]
    
    # =========================================================================
    # Multi-word Commands
    # =========================================================================
    
    def test_parse_ci_status(self, parser):
        """Test parsing ci-status command."""
        result = parser.parse(
            text="@agent ci-status",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "ci-status"
    
    def test_parse_ci_alias(self, parser):
        """Test parsing ci alias."""
        result = parser.parse(
            text="@agent ci",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "ci-status"
    
    # =========================================================================
    # Natural Language Questions
    # =========================================================================
    
    def test_parse_question(self, parser):
        """Test parsing natural language question."""
        result = parser.parse(
            text="@agent how does authentication work?",
            platform=Platform.SLACK,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "ask"
        assert "how does authentication work?" in result.args[0]
    
    def test_parse_question_without_mark(self, parser):
        """Test parsing question starting with 'what'."""
        result = parser.parse(
            text="@agent what is the purpose of this function",
            platform=Platform.SLACK,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "ask"
    
    # =========================================================================
    # Bot Tag Variations
    # =========================================================================
    
    def test_parse_with_claude_tag(self, parser):
        """Test parsing with @claude tag."""
        result = parser.parse(
            text="@claude approve",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "approve"
    
    def test_parse_case_insensitive(self, parser):
        """Test case insensitive parsing."""
        result = parser.parse(
            text="@AGENT APPROVE",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "approve"
    
    def test_parse_no_bot_mention(self, parser):
        """Test parsing without bot mention returns None."""
        result = parser.parse(
            text="just a regular comment",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is None
    
    # =========================================================================
    # Platform Filtering
    # =========================================================================
    
    def test_github_only_command(self, parser):
        """Test update-title only available on GitHub."""
        # Should work on GitHub
        result = parser.parse(
            text="@agent update-title new title",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is not None
    
    # =========================================================================
    # Unknown Commands
    # =========================================================================
    
    def test_unknown_command(self, parser):
        """Test parsing unknown command."""
        result = parser.parse(
            text="@agent foobar",
            platform=Platform.GITHUB,
            context={}
        )
        
        assert result is not None
        assert result.command_name == "unknown"
    
    # =========================================================================
    # Context Preservation
    # =========================================================================
    
    def test_context_preserved(self, parser):
        """Test that context is passed through."""
        context = {
            "pr_number": 123,
            "repository": "org/repo",
            "task_id": "task-123"
        }
        
        result = parser.parse(
            text="@agent approve",
            platform=Platform.GITHUB,
            context=context
        )
        
        assert result is not None
        assert result.context["pr_number"] == 123
        assert result.context["repository"] == "org/repo"
        assert result.context["task_id"] == "task-123"


class TestCommandLoader:
    """Test command loading functionality."""
    
    @pytest.fixture
    def loader(self):
        """Create loader instance."""
        return CommandLoader()
    
    def test_load_all_commands(self, loader):
        """Test loading all commands."""
        commands = loader.load_all()
        
        assert len(commands) > 0
        assert "approve" in commands
        assert "reject" in commands
        assert "help" in commands
    
    def test_get_command_by_name(self, loader):
        """Test getting command by name."""
        cmd = loader.get_command("approve")
        
        assert cmd is not None
        assert cmd.name == "approve"
        assert "lgtm" in cmd.aliases
    
    def test_get_command_by_alias(self, loader):
        """Test getting command by alias."""
        cmd = loader.get_command("lgtm")
        
        assert cmd is not None
        assert cmd.name == "approve"
    
    def test_get_nonexistent_command(self, loader):
        """Test getting nonexistent command returns None."""
        cmd = loader.get_command("nonexistent")
        
        assert cmd is None
    
    def test_commands_have_descriptions(self, loader):
        """Test all commands have descriptions."""
        commands = loader.load_all()
        
        for name, cmd in commands.items():
            assert cmd.description, f"Command {name} has no description"
            assert len(cmd.description) > 10, f"Command {name} description too short"
    
    def test_commands_have_usage(self, loader):
        """Test all commands have usage."""
        commands = loader.load_all()
        
        for name, cmd in commands.items():
            assert cmd.usage, f"Command {name} has no usage"
    
    def test_get_commands_for_platform(self, loader):
        """Test filtering commands by platform."""
        github_commands = loader.get_commands_for_platform(Platform.GITHUB)
        
        assert len(github_commands) > 0
        
        # All returned commands should include GitHub as platform
        for cmd in github_commands:
            assert Platform.GITHUB in cmd.platforms


class TestHelpGeneration:
    """Test help text generation."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return CommandParser()
    
    def test_full_help(self, parser):
        """Test full help text generation."""
        help_text = parser.get_help()
        
        assert "Commands" in help_text
        assert "approve" in help_text
        assert "@agent" in help_text
    
    def test_specific_command_help(self, parser):
        """Test help for specific command."""
        help_text = parser.get_help("approve")
        
        assert "approve" in help_text
        assert "Usage" in help_text
        assert "lgtm" in help_text  # Alias should be shown
    
    def test_unknown_command_help(self, parser):
        """Test help for unknown command."""
        help_text = parser.get_help("nonexistent")
        
        assert "Unknown command" in help_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
