"""TDD tests for Slack task summary extraction."""

import pytest


class TestSlackSummaryExtraction:
    """Test task summary extraction from result strings."""
    
    def test_extract_task_summary_with_sections(self):
        """
        Business Rule: Extract structured summary from result string.
        Behavior: Parses summary, what_was_done, and key_insights sections.
        """
        from api.webhooks.slack.utils import extract_task_summary
        
        result = """
## Summary
This task analyzed the authentication flow and identified security improvements.

## What Was Done
- Reviewed authentication code
- Identified 3 security vulnerabilities
- Created fix plan

## Key Insights
- Password hashing needs improvement
- Session management has issues
- OAuth flow is secure
"""
        
        task_metadata = {"classification": "WORKFLOW"}
        
        summary = extract_task_summary(result, task_metadata)
        
        assert summary.summary == "This task analyzed the authentication flow and identified security improvements."
        assert "Reviewed authentication code" in (summary.what_was_done or "")
        assert "Password hashing needs improvement" in (summary.key_insights or "")
        assert summary.classification == "WORKFLOW"
    
    def test_extract_task_summary_missing_sections(self):
        """
        Business Rule: Handle missing sections gracefully.
        Behavior: Returns empty strings for missing sections.
        """
        from api.webhooks.slack.utils import extract_task_summary
        
        result = "Task completed successfully."
        task_metadata = {}
        
        summary = extract_task_summary(result, task_metadata)
        
        assert summary.summary == "Task completed successfully."
        assert summary.what_was_done is None or summary.what_was_done == ""
        assert summary.key_insights is None or summary.key_insights == ""
        assert summary.classification == "SIMPLE"
    
    def test_extract_task_classification(self):
        """
        Business Rule: Extract task classification from metadata or infer from content.
        Behavior: Returns WORKFLOW, SIMPLE, or CUSTOM classification.
        """
        from api.webhooks.slack.utils import extract_task_summary
        
        # Test with explicit classification
        result = "Task done"
        task_metadata = {"classification": "WORKFLOW"}
        summary = extract_task_summary(result, task_metadata)
        assert summary.classification == "WORKFLOW"
        
        # Test with inferred classification (has sections = WORKFLOW)
        result = """
## Summary
Test

## What Was Done
Something
"""
        task_metadata = {}
        summary = extract_task_summary(result, task_metadata)
        assert summary.classification == "WORKFLOW"
        
        # Test simple task (no sections)
        result = "Task completed"
        task_metadata = {}
        summary = extract_task_summary(result, task_metadata)
        assert summary.classification == "SIMPLE"
    
    def test_extract_task_summary_preserves_formatting(self):
        """
        Business Rule: Preserve markdown formatting in extracted sections.
        Behavior: Markdown formatting is preserved in summary sections.
        """
        from api.webhooks.slack.utils import extract_task_summary
        
        result = """
## Summary
Task **completed** with *emphasis*.

## What Was Done
- Item 1
- Item 2
- Item 3

## Key Insights
> Important note here
"""
        
        task_metadata = {}
        summary = extract_task_summary(result, task_metadata)
        
        assert "**completed**" in summary.summary
        assert "*emphasis*" in summary.summary
        assert "- Item 1" in (summary.what_was_done or "")
        assert "> Important note" in (summary.key_insights or "")
