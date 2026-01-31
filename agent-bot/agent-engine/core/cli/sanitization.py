import re


def sanitize_sensitive_content(content: str) -> str:
    if not content:
        return content

    if isinstance(content, list):
        content = "\n".join(str(item) for item in content)
    elif not isinstance(content, str):
        content = str(content) if content else ""

    sensitive_patterns = [
        (
            r"(JIRA_API_TOKEN|JIRA_EMAIL|GITHUB_TOKEN|SLACK_BOT_TOKEN|"
            r"SLACK_WEBHOOK_SECRET|GITHUB_WEBHOOK_SECRET|JIRA_WEBHOOK_SECRET)"
            r"\s*=\s*([^\s\n]+)",
            r"\1=***REDACTED***",
        ),
        (
            r"(password|passwd|pwd|token|secret|api_key|apikey|"
            r"access_token|refresh_token)\s*[:=]\s*([^\s\n]+)",
            r"\1=***REDACTED***",
        ),
        (r"(Authorization:\s*Bearer\s+)([^\s\n]+)", r"\1***REDACTED***"),
        (r"(Authorization:\s*Basic\s+)([^\s\n]+)", r"\1***REDACTED***"),
        (
            r'(["\']?token["\']?\s*[:=]\s*["\']?)([^"\'\s\n]+)(["\']?)',
            r"\1***REDACTED***\3",
        ),
        (
            r'(["\']?password["\']?\s*[:=]\s*["\']?)([^"\'\s\n]+)(["\']?)',
            r"\1***REDACTED***\3",
        ),
    ]

    sanitized = content
    for pattern in sensitive_patterns:
        sanitized = re.sub(pattern[0], pattern[1], sanitized, flags=re.IGNORECASE)

    return sanitized


def contains_sensitive_data(content: str) -> bool:
    if not content:
        return False

    if not isinstance(content, str):
        content = str(content) if content else ""

    sensitive_indicators = [
        r"JIRA_API_TOKEN\s*=",
        r"GITHUB_TOKEN\s*=",
        r"SLACK_BOT_TOKEN\s*=",
        r"password\s*[:=]",
        r"token\s*[:=]",
        r"secret\s*[:=]",
        r"Authorization:\s*(Bearer|Basic)",
    ]

    for pattern in sensitive_indicators:
        if re.search(pattern, content, re.IGNORECASE):
            return True

    return False
