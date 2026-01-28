from typing import Optional


class MessageFormatter:

    MAX_GITHUB_COMMENT = 8000
    MAX_GITHUB_COMMENT_SUCCESS = 4000
    MAX_JIRA_COMMENT = 32767
    MAX_SLACK_MESSAGE = 4000
    MAX_SLACK_BLOCK_TEXT = 3000

    @staticmethod
    def truncate(
        text: str,
        max_length: int,
        suffix: str = "\n\n... (truncated)",
        preserve_ratio: float = 0.8,
    ) -> str:
        if len(text) <= max_length:
            return text

        available = max_length - len(suffix)
        if available <= 0:
            return suffix

        truncated = text[:available]

        min_preserve = int(available * preserve_ratio)

        last_period = truncated.rfind(". ")
        if last_period < 0:
            last_period = truncated.rfind(".")

        last_newline = truncated.rfind("\n")

        truncate_at = max(last_period, last_newline)

        if truncate_at > min_preserve:
            if truncate_at == last_period:
                truncated = truncated[:truncate_at + 1]
            else:
                truncated = truncated[:truncate_at]

        return truncated + suffix

    @staticmethod
    def format_github_comment(
        message: str,
        success: bool,
        cost_usd: float = 0.0,
        max_length: Optional[int] = None,
    ) -> str:
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

        if max_length is None:
            max_length = (
                MessageFormatter.MAX_GITHUB_COMMENT_SUCCESS
                if success
                else MessageFormatter.MAX_GITHUB_COMMENT
            )

        cost_suffix = ""
        if success and cost_usd > 0:
            cost_suffix = f"\n\n💰 Cost: ${cost_usd:.4f}"

        available_length = max_length - len(cost_suffix)
        if len(formatted) > available_length:
            formatted = MessageFormatter.truncate(formatted, available_length)

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
        parts = []

        if success:
            parts.append("(/) *Task Completed*")
        else:
            parts.append("(x) *Task Failed*")

        parts.append("")
        parts.append(message)

        if pr_url:
            parts.append("")
            parts.append(f"*Pull Request:* [{pr_url}]")

        if cost_usd > 0:
            parts.append("")
            parts.append(f"*Cost:* ${cost_usd:.4f}")

        formatted = "\n".join(parts)

        if len(formatted) > max_length:
            formatted = MessageFormatter.truncate(formatted, max_length)

        return formatted

    @staticmethod
    def format_slack_message(
        message: str,
        success: bool,
        max_length: int = 4000,
    ) -> str:
        status_emoji = "✅" if success else "❌"
        formatted = f"{status_emoji} {message}"

        if len(formatted) > max_length:
            formatted = MessageFormatter.truncate(formatted, max_length)

        return formatted

    @staticmethod
    def format_cost(cost_usd: float) -> str:
        if cost_usd <= 0:
            return ""
        return f"${cost_usd:.4f}"

    @staticmethod
    def preview(text: str, max_length: int = 100) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
