"""
Task summary extraction.

Extracts structured summary from task results.
"""

import re
from typing import Optional

from domain.models.notifications import TaskSummary


def extract_task_summary(
    result: str,
    metadata: Optional[dict] = None,
) -> TaskSummary:
    """
    Extract structured task summary from task result.

    Parses the result to extract:
    - Summary: Brief description of what was done
    - Classification: Task complexity
    - What was done: Detailed actions
    - Key insights: Important findings

    Args:
        result: Raw task result string
        metadata: Optional task metadata with classification

    Returns:
        TaskSummary with extracted information

    Example:
        >>> summary = extract_task_summary("Review completed. Found 3 issues.")
        >>> summary.summary
        'Review completed. Found 3 issues.'
    """
    metadata = metadata or {}

    # Get classification from metadata
    classification = metadata.get("classification", "SIMPLE")

    # Create default summary from first part of result
    if not result:
        return TaskSummary(
            summary="Task completed",
            classification=classification,
        )

    # Truncate long results for summary
    max_summary_length = 200
    summary_text = result.strip()

    if len(summary_text) > max_summary_length:
        # Try to truncate at sentence boundary
        truncated = summary_text[:max_summary_length]

        # Find last sentence end
        last_period = truncated.rfind(". ")
        last_newline = truncated.rfind("\n")
        truncate_at = max(last_period, last_newline)

        if truncate_at > max_summary_length * 0.5:
            summary_text = truncated[:truncate_at + 1].strip()
        else:
            summary_text = truncated + "..."

    # Try to extract structured information using patterns
    what_was_done = None
    key_insights = None

    # Look for common patterns in results
    # Pattern: "## What was done" or "### Summary"
    what_done_match = re.search(
        r"(?:##?\s*)?(?:What was done|Summary|Actions taken)[:\s]*(.+?)(?=(?:##|$))",
        result,
        re.IGNORECASE | re.DOTALL
    )
    if what_done_match:
        what_was_done = what_done_match.group(1).strip()[:300]

    # Pattern: "## Key insights" or "### Findings"
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
