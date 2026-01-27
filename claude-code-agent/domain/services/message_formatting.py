"""
Unified message formatting and truncation.

This module consolidates duplicated message formatting logic from:
- github/utils.py: message truncation (~8 occurrences)
- jira/utils.py: _truncate_text, comment formatting
- slack/utils.py: message truncation

Provides:
- Intelligent truncation at natural boundaries
- Platform-specific comment formatting
- Cost display formatting
"""

from typing import Optional


class MessageFormatter:
    """
    Unified message formatting and truncation utilities.

    Provides consistent message formatting across all webhook handlers.
    """

    # Default max lengths for different contexts
    MAX_GITHUB_COMMENT = 8000
    MAX_GITHUB_COMMENT_SUCCESS = 4000
    MAX_JIRA_COMMENT = 32767  # Jira limit
    MAX_SLACK_MESSAGE = 4000
    MAX_SLACK_BLOCK_TEXT = 3000

    @staticmethod
    def truncate(
        text: str,
        max_length: int,
        suffix: str = "\n\n... (truncated)",
        preserve_ratio: float = 0.8,
    ) -> str:
        """
        Truncate text at natural boundaries (sentence/newline).

        Args:
            text: Text to truncate
            max_length: Maximum length before truncation
            suffix: Suffix to add when truncated
            preserve_ratio: Min ratio of max_length to preserve before boundary search

        Returns:
            Original text if under max_length, otherwise truncated text with suffix

        Example:
            >>> MessageFormatter.truncate("Hello. World.", max_length=10)
            'Hello.... (truncated)'
        """
        if len(text) <= max_length:
            return text

        # Reserve space for suffix
        available = max_length - len(suffix)
        if available <= 0:
            return suffix

        # Get truncated portion
        truncated = text[:available]

        # Find natural boundary (period or newline) in last portion
        min_preserve = int(available * preserve_ratio)

        # Look for sentence boundary (period followed by space or end)
        last_period = truncated.rfind(". ")
        if last_period < 0:
            last_period = truncated.rfind(".")

        # Look for newline boundary
        last_newline = truncated.rfind("\n")

        # Use the boundary that's furthest along but still after min_preserve
        truncate_at = max(last_period, last_newline)

        if truncate_at > min_preserve:
            # Truncate at natural boundary
            if truncate_at == last_period:
                truncated = truncated[:truncate_at + 1]  # Include the period
            else:
                truncated = truncated[:truncate_at]  # Don't include newline

        return truncated + suffix

    @staticmethod
    def format_github_comment(
        message: str,
        success: bool,
        cost_usd: float = 0.0,
        max_length: Optional[int] = None,
    ) -> str:
        """
        Format a message for GitHub comment.

        Args:
            message: The message content
            success: Whether the task succeeded
            cost_usd: Cost in USD (shown only for success)
            max_length: Maximum length (defaults based on success)

        Returns:
            Formatted GitHub comment
        """
        # Add status prefix
        if success:
            if message == "❌":
                formatted = "❌"
            else:
                formatted = f"✅ {message}"
        else:
            if message == "❌":
                formatted = "❌"
            else:
                formatted = f"❌ {message}"

        # Determine max length
        if max_length is None:
            max_length = (
                MessageFormatter.MAX_GITHUB_COMMENT_SUCCESS
                if success
                else MessageFormatter.MAX_GITHUB_COMMENT
            )

        # Reserve space for cost if needed
        cost_suffix = ""
        if success and cost_usd > 0:
            cost_suffix = f"\n\n💰 Cost: ${cost_usd:.4f}"

        # Truncate if needed (accounting for cost suffix)
        available_length = max_length - len(cost_suffix)
        if len(formatted) > available_length:
            formatted = MessageFormatter.truncate(formatted, available_length)

        # Add cost
        if cost_suffix:
            formatted += cost_suffix

        return formatted

    @staticmethod
    def format_jira_comment(
        message: str,
        success: bool,
        cost_usd: float = 0.0,
        pr_url: Optional[str] = None,
        max_length: int = 32767,
    ) -> str:
        """
        Format a message for Jira comment.

        Args:
            message: The message content
            success: Whether the task succeeded
            cost_usd: Cost in USD
            pr_url: Pull request URL if available
            max_length: Maximum length

        Returns:
            Formatted Jira comment (uses Jira wiki markup)
        """
        # Build the comment
        parts = []

        # Status prefix (Jira wiki markup)
        if success:
            parts.append("(/) *Task Completed*")
        else:
            parts.append("(x) *Task Failed*")

        parts.append("")  # Empty line
        parts.append(message)

        # Add PR URL if present
        if pr_url:
            parts.append("")
            parts.append(f"*Pull Request:* [{pr_url}]")

        # Add cost if present
        if cost_usd > 0:
            parts.append("")
            parts.append(f"*Cost:* ${cost_usd:.4f}")

        formatted = "\n".join(parts)

        # Truncate if needed
        if len(formatted) > max_length:
            formatted = MessageFormatter.truncate(formatted, max_length)

        return formatted

    @staticmethod
    def format_slack_message(
        message: str,
        success: bool,
        max_length: int = 4000,
    ) -> str:
        """
        Format a message for Slack.

        Args:
            message: The message content
            success: Whether the task succeeded
            max_length: Maximum length

        Returns:
            Formatted Slack message
        """
        # Add status prefix
        status_emoji = "✅" if success else "❌"
        formatted = f"{status_emoji} {message}"

        # Truncate if needed
        if len(formatted) > max_length:
            formatted = MessageFormatter.truncate(formatted, max_length)

        return formatted

    @staticmethod
    def format_cost(cost_usd: float) -> str:
        """
        Format cost for display.

        Args:
            cost_usd: Cost in USD

        Returns:
            Formatted cost string
        """
        if cost_usd <= 0:
            return ""
        return f"${cost_usd:.4f}"

    @staticmethod
    def preview(text: str, max_length: int = 100) -> str:
        """
        Create a preview of text for logging.

        Args:
            text: Text to preview
            max_length: Maximum preview length

        Returns:
            Shortened text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
