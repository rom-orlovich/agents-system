"""Unit tests for Jira PR URL extraction functions."""

import pytest
from api.webhooks.jira.utils import extract_pr_url, extract_pr_routing


class TestExtractPRURL:
    """Test PR URL extraction from text."""
    
    def test_extracts_pr_url_from_text(self):
        """Extract PR URL from text containing GitHub PR link."""
        text = "Task completed. PR: https://github.com/owner/repo/pull/123"
        result = extract_pr_url(text)
        assert result == "https://github.com/owner/repo/pull/123"
    
    def test_extracts_pr_url_with_pulls_path(self):
        """Extract PR URL with /pulls/ path."""
        text = "See https://github.com/test/repo/pulls/456 for details"
        result = extract_pr_url(text)
        assert result == "https://github.com/test/repo/pulls/456"
    
    def test_returns_none_when_no_pr_url(self):
        """Return None when no PR URL found."""
        text = "Task completed successfully"
        result = extract_pr_url(text)
        assert result is None
    
    def test_returns_none_for_empty_text(self):
        """Return None for empty text."""
        result = extract_pr_url("")
        assert result is None
    
    def test_extracts_first_pr_url(self):
        """Extract first PR URL when multiple present."""
        text = "PR1: https://github.com/owner/repo/pull/123 and PR2: https://github.com/owner/repo/pull/456"
        result = extract_pr_url(text)
        assert result == "https://github.com/owner/repo/pull/123"


class TestExtractPRRouting:
    """Test PR routing extraction from PR URL."""
    
    def test_extracts_repo_and_pr_number(self):
        """Extract repo and PR number from PR URL."""
        pr_url = "https://github.com/owner/repo/pull/123"
        result = extract_pr_routing(pr_url)
        assert result is not None
        assert result.repo == "owner/repo"
        assert result.pr_number == 123
    
    def test_extracts_from_pulls_path(self):
        """Extract from /pulls/ path."""
        pr_url = "https://github.com/test/example/pulls/456"
        result = extract_pr_routing(pr_url)
        assert result is not None
        assert result.repo == "test/example"
        assert result.pr_number == 456
    
    def test_returns_empty_dict_for_invalid_url(self):
        """Return None for invalid URL."""
        pr_url = "https://github.com/invalid"
        result = extract_pr_routing(pr_url)
        assert result is None
    
    def test_returns_empty_dict_for_empty_url(self):
        """Return None for empty URL."""
        result = extract_pr_routing("")
        assert result is None
    
    def test_case_insensitive_matching(self):
        """Handle case-insensitive matching."""
        pr_url = "https://github.com/Owner/Repo/pull/789"
        result = extract_pr_routing(pr_url)
        assert result is not None
        assert result.repo == "Owner/Repo"
        assert result.pr_number == 789
