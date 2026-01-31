import re

SENSITIVE_PATTERNS: list[tuple[str, str] | tuple[str, str, int]] = [
    (
        r"(JIRA_API_TOKEN|JIRA_EMAIL|GITHUB_TOKEN|SLACK_BOT_TOKEN|"
        r"SLACK_WEBHOOK_SECRET|GITHUB_WEBHOOK_SECRET|JIRA_WEBHOOK_SECRET)"
        r"\s*=\s*([^\s\n]+)",
        r"\1=***REDACTED***",
    ),
    (
        r"(password|passwd|pwd|token|secret|api_key|apikey|access_token|refresh_token)"
        r"\s*[:=]\s*([^\s\n]+)",
        r"\1=***REDACTED***",
        re.IGNORECASE,
    ),
    (r"(Authorization:\s*Bearer\s+)([^\s\n]+)", r"\1***REDACTED***"),
    (r"(Authorization:\s*Basic\s+)([^\s\n]+)", r"\1***REDACTED***"),
    (
        r'(["\']?token["\']?\s*[:=]\s*["\']?)([^"\'\s\n]+)(["\']?)',
        r"\1***REDACTED***\3",
        re.IGNORECASE,
    ),
    (
        r'(["\']?password["\']?\s*[:=]\s*["\']?)([^"\'\s\n]+)(["\']?)',
        r"\1***REDACTED***\3",
        re.IGNORECASE,
    ),
]

SENSITIVE_INDICATORS: list[str] = [
    r"JIRA_API_TOKEN\s*=",
    r"GITHUB_TOKEN\s*=",
    r"SLACK_BOT_TOKEN\s*=",
    r"password\s*[:=]",
    r"token\s*[:=]",
    r"secret\s*[:=]",
    r"Authorization:\s*(Bearer|Basic)",
]


def sanitize_sensitive_content(content: str | list[str] | None) -> str:
    if not content:
        return ""

    if isinstance(content, list):
        content = "\n".join(str(item) for item in content)
    elif not isinstance(content, str):
        content = str(content)

    sanitized = content
    for pattern in SENSITIVE_PATTERNS:
        if len(pattern) == 2:
            sanitized = re.sub(pattern[0], pattern[1], sanitized)
        else:
            sanitized = re.sub(pattern[0], pattern[1], sanitized, flags=pattern[2])

    return sanitized


def contains_sensitive_data(content: str | None) -> bool:
    if not content:
        return False

    content_str = str(content) if not isinstance(content, str) else content

    return any(
        re.search(pattern, content_str, re.IGNORECASE) for pattern in SENSITIVE_INDICATORS
    )
