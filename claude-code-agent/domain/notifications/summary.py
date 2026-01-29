import re
from typing import Optional

from domain.models.notifications import TaskSummary


def extract_task_summary(
    result: str,
    metadata: Optional[dict] = None,
) -> TaskSummary:
    metadata = metadata or {}

    classification = metadata.get("classification", "SIMPLE")

    if not result:
        return TaskSummary(
            summary="Task completed",
            classification=classification,
        )

    max_summary_length = 200
    summary_text = result.strip()

    if len(summary_text) > max_summary_length:
        truncated = summary_text[:max_summary_length]

        last_period = truncated.rfind(". ")
        last_newline = truncated.rfind("\n")
        truncate_at = max(last_period, last_newline)

        if truncate_at > max_summary_length * 0.5:
            summary_text = truncated[:truncate_at + 1].strip()
        else:
            summary_text = truncated + "..."

    what_was_done = None
    key_insights = None

    what_done_match = re.search(
        r"(?:##?\s*)?(?:What was done|Summary|Actions taken)[:\s]*(.+?)(?=(?:##|$))",
        result,
        re.IGNORECASE | re.DOTALL
    )
    if what_done_match:
        what_was_done = what_done_match.group(1).strip()[:300]

    insights_match = re.search(
        r"(?:##?\s*)?(?:Key insights|Findings|Notes)[:\s]*(.+?)(?=(?:##|$))",
        result,
        re.IGNORECASE | re.DOTALL
    )
    if insights_match:
        key_insights = insights_match.group(1).strip()[:300]

    return TaskSummary(
        summary=summary_text,
        classification=classification,
        what_was_done=what_was_done,
        key_insights=key_insights,
    )
