"""Parse bot commands from user messages.

This module parses incoming messages (from GitHub comments, Slack messages, 
Jira comments) to extract bot commands.

Usage:
    from shared.commands import CommandParser
    
    parser = CommandParser()
    
    # Parse a GitHub comment
    result = parser.parse(
        text="@agent approve",
        platform=Platform.GITHUB,
        context={"pr_number": 123, "repository": "org/repo"}
    )
    
    if result:
        print(f"Command: {result.command_name}")
        print(f"Args: {result.args}")
"""

from __future__ import annotations

import re
from typing import Optional, List, Dict, Any
import logging

from ..models import ParsedCommand, CommandDefinition
from ..enums import CommandType, Platform
from ..constants import BOT_CONFIG
from .loader import get_loader

logger = logging.getLogger("command_parser")


class CommandParser:
    """Parse commands from user messages.
    
    Supports multiple bot tags (@agent, @claude, etc.) and handles
    aliases, multi-word commands, and natural language questions.
    
    Attributes:
        bot_tags: List of trigger tags (e.g., ["@agent", "@claude"])
        loader: CommandLoader instance
    
    Example:
        parser = CommandParser()
        
        # Simple command
        result = parser.parse("@agent approve", Platform.GITHUB, {})
        assert result.command_name == "approve"
        
        # Command with alias
        result = parser.parse("@agent lgtm", Platform.GITHUB, {})
        assert result.command_name == "approve"
        
        # Command with arguments
        result = parser.parse("@agent reject too risky", Platform.GITHUB, {})
        assert result.command_name == "reject"
        assert result.args == ["too risky"]
        
        # Natural language question
        result = parser.parse("@agent how does auth work?", Platform.SLACK, {})
        assert result.command_name == "ask"
    """
    
    # Words that indicate a natural language question
    QUESTION_STARTERS = {"how", "what", "why", "where", "when", "who", "which", "can", "could", "would", "should", "is", "are", "do", "does"}
    
    def __init__(self):
        """Initialize parser with bot configuration."""
        self.bot_tags = [tag.strip().lower() for tag in BOT_CONFIG.tags]
        self.loader = get_loader()
    
    def parse(
        self,
        text: str,
        platform: Platform,
        context: Dict[str, Any],
    ) -> Optional[ParsedCommand]:
        """Parse command from text.
        
        Args:
            text: Full message text
            platform: Where the message came from
            context: Platform-specific context (pr_number, issue_key, etc.)
            
        Returns:
            ParsedCommand if a valid command was found, None otherwise.
        """
        if not text:
            return None
        
        text_lower = text.strip().lower()
        
        # Find bot trigger
        command_text = None
        trigger_used = None
        
        for tag in self.bot_tags:
            if tag in text_lower:
                # Find the exact position in original text (case-insensitive)
                idx = text_lower.find(tag)
                if idx != -1:
                    # Get text after the trigger, preserving original case
                    command_text = text[idx + len(tag):].strip()
                    trigger_used = tag
                    break
        
        if command_text is None:
            logger.debug(f"No bot trigger found in: {text[:50]}...")
            return None
        
        logger.debug(f"Found trigger '{trigger_used}', command text: '{command_text}'")
        
        # Parse the command
        return self._parse_command_text(command_text, platform, context)
    
    def _parse_command_text(
        self,
        command_text: str,
        platform: Platform,
        context: Dict[str, Any],
    ) -> Optional[ParsedCommand]:
        """Parse the command portion of the text.
        
        Args:
            command_text: Text after the bot trigger
            platform: Where the message came from
            context: Platform-specific context
            
        Returns:
            ParsedCommand if valid, None otherwise.
        """
        if not command_text:
            # Just the trigger with nothing after = show help
            return self._create_parsed_command(
                "help", [], command_text, platform, context
            )
        
        # Split into words
        words = command_text.split()
        first_word = words[0].lower() if words else ""
        rest = " ".join(words[1:]) if len(words) > 1 else ""
        
        # Check for multi-word commands first (e.g., "list repos", "ci status")
        if len(words) >= 2:
            two_word = f"{first_word}-{words[1].lower()}"
            if self.loader.get_command(two_word):
                rest = " ".join(words[2:]) if len(words) > 2 else ""
                return self._create_parsed_command(
                    two_word, [rest] if rest else [], command_text, platform, context
                )
            
            # Also try with space (e.g., "list repos")
            two_word_space = f"{first_word} {words[1].lower()}"
            if self.loader.get_command(two_word_space):
                rest = " ".join(words[2:]) if len(words) > 2 else ""
                return self._create_parsed_command(
                    two_word_space, [rest] if rest else [], command_text, platform, context
                )
        
        # Check for direct command match
        cmd = self.loader.get_command(first_word)
        if cmd:
            # Check platform support
            if platform not in cmd.platforms:
                logger.debug(f"Command '{first_word}' not available on {platform}")
                return None
            
            args = [rest] if rest else []
            return self._create_parsed_command(
                first_word, args, command_text, platform, context
            )
        
        # Check if it looks like a question (natural language)
        if self._is_question(command_text):
            return self._create_parsed_command(
                "ask", [command_text], command_text, platform, context
            )
        
        # Unknown command
        logger.debug(f"Unknown command: {first_word}")
        return self._create_parsed_command(
            "unknown", [command_text], command_text, platform, context
        )
    
    def _create_parsed_command(
        self,
        command_name: str,
        args: List[str],
        raw_text: str,
        platform: Platform,
        context: Dict[str, Any],
    ) -> ParsedCommand:
        """Create a ParsedCommand object.
        
        Args:
            command_name: Name or alias of the command
            args: Extracted arguments
            raw_text: Original command text
            platform: Where the message came from
            context: Platform-specific context
            
        Returns:
            ParsedCommand object
        """
        # Look up the canonical command name
        cmd_def = self.loader.get_command(command_name)
        
        # Map to CommandType enum
        try:
            cmd_type = CommandType(command_name.replace("-", "_"))
        except ValueError:
            # Try the handler name
            if cmd_def and hasattr(CommandType, cmd_def.name.upper().replace("-", "_")):
                cmd_type = CommandType[cmd_def.name.upper().replace("-", "_")]
            else:
                cmd_type = CommandType.UNKNOWN
        
        # Get canonical name if available
        canonical_name = cmd_def.name if cmd_def else command_name
        
        return ParsedCommand(
            command_type=cmd_type,
            command_name=canonical_name,
            definition=cmd_def,
            args=args,
            raw_text=raw_text,
            platform=platform,
            context=context,
        )
    
    def _is_question(self, text: str) -> bool:
        """Check if text looks like a natural language question.
        
        Args:
            text: Text to check
            
        Returns:
            True if it looks like a question
        """
        text_lower = text.lower().strip()
        
        # Ends with question mark
        if text.rstrip().endswith("?"):
            return True
        
        # Starts with question word
        first_word = text_lower.split()[0] if text_lower.split() else ""
        if first_word in self.QUESTION_STARTERS:
            return True
        
        return False
    
    def get_help(self, command_name: Optional[str] = None) -> str:
        """Generate help text.
        
        Args:
            command_name: Specific command or None for all
            
        Returns:
            Formatted help text
        """
        if command_name:
            cmd = self.loader.get_command(command_name)
            if not cmd:
                return f"❓ Unknown command: `{command_name}`\n\nUse `@agent help` to see all commands."
            
            # Format single command help
            lines = [
                f"## {cmd.name}",
                "",
                cmd.description,
                "",
                f"**Usage:** `{cmd.usage}`",
            ]
            
            if cmd.aliases:
                aliases_str = ", ".join(f"`{a}`" for a in cmd.aliases[:5])
                lines.append(f"**Aliases:** {aliases_str}")
            
            if cmd.examples:
                lines.append("")
                lines.append("**Examples:**")
                for ex in cmd.examples[:3]:
                    lines.append(f"- `{ex}`")
            
            if cmd.parameters:
                lines.append("")
                lines.append("**Parameters:**")
                for param in cmd.parameters:
                    req = "required" if param.required else "optional"
                    lines.append(f"- `{param.name}` ({param.param_type}, {req}): {param.description}")
            
            return "\n".join(lines)
        
        # Full help
        commands = self.loader.load_all()
        
        # Group by category (based on handler prefix)
        categories = {
            "Core": [],
            "CI/CD": [],
            "Code": [],
            "Discovery": [],
            "PR": [],
            "Jira": [],
        }
        
        for name, cmd in commands.items():
            if name in ("approve", "reject", "improve", "status", "help"):
                categories["Core"].append(cmd)
            elif "ci" in name:
                categories["CI/CD"].append(cmd)
            elif name in ("ask", "explain", "find", "diff"):
                categories["Code"].append(cmd)
            elif name in ("discover", "list-repos", "list-files"):
                categories["Discovery"].append(cmd)
            elif name in ("update-title", "add-tests", "fix-lint"):
                categories["PR"].append(cmd)
            elif "jira" in name or name == "link-pr":
                categories["Jira"].append(cmd)
        
        lines = [
            f"## {BOT_CONFIG.emoji} {BOT_CONFIG.name} Commands",
            "",
        ]
        
        for category, cmds in categories.items():
            if not cmds:
                continue
            
            lines.append(f"### {category}")
            lines.append("| Command | Description |")
            lines.append("|---------|-------------|")
            
            for cmd in cmds:
                desc = cmd.description.split("\n")[0][:50]
                lines.append(f"| `@agent {cmd.name}` | {desc} |")
            
            lines.append("")
        
        lines.append("---")
        lines.append(f"Use `@agent help <command>` for details on a specific command.")
        
        return "\n".join(lines)
