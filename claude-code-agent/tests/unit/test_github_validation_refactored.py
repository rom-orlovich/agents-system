"""TDD tests for GitHub validate_response_format refactoring (Phase 2)."""

import pytest


class TestGitHubValidateResponseFormat:
    """Test GitHub validate_response_format is available in validation.py."""

    def test_validate_response_format_can_be_imported(self):
        """validate_response_format should be importable from github.validation."""
        from api.webhooks.github.validation import validate_response_format

        assert callable(validate_response_format)

    def test_validate_pr_review_format_valid(self):
        """Validate correct PR review format passes."""
        from api.webhooks.github.validation import validate_response_format

        valid_pr_review = """## PR Review

### Summary
This is a summary.

### Code Quality
Good code quality.

### Findings
- Finding 1
- Finding 2

### Verdict
approve

*Reviewed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(valid_pr_review, "pr_review")

        assert is_valid is True
        assert error_msg == ""

    def test_validate_pr_review_missing_header(self):
        """PR review without '## PR Review' header should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_pr_review = """### Summary
Some summary

### Code Quality
Good

### Findings
None

### Verdict
approve

*Reviewed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(invalid_pr_review, "pr_review")

        assert is_valid is False
        assert "PR Review" in error_msg

    def test_validate_pr_review_missing_summary(self):
        """PR review without Summary section should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_pr_review = """## PR Review

### Code Quality
Good

### Findings
None

### Verdict
approve

*Reviewed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(invalid_pr_review, "pr_review")

        assert is_valid is False
        assert "Summary" in error_msg

    def test_validate_pr_review_missing_code_quality(self):
        """PR review without Code Quality section should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_pr_review = """## PR Review

### Summary
Summary here

### Findings
None

### Verdict
approve

*Reviewed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(invalid_pr_review, "pr_review")

        assert is_valid is False
        assert "Code Quality" in error_msg

    def test_validate_pr_review_missing_findings(self):
        """PR review without Findings section should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_pr_review = """## PR Review

### Summary
Summary here

### Code Quality
Good

### Verdict
approve

*Reviewed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(invalid_pr_review, "pr_review")

        assert is_valid is False
        assert "Findings" in error_msg

    def test_validate_pr_review_missing_verdict(self):
        """PR review without Verdict section should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_pr_review = """## PR Review

### Summary
Summary here

### Code Quality
Good

### Findings
None

*Reviewed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(invalid_pr_review, "pr_review")

        assert is_valid is False
        assert "Verdict" in error_msg

    def test_validate_pr_review_invalid_verdict_value(self):
        """PR review with invalid verdict should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_pr_review = """## PR Review

### Summary
Summary here

### Code Quality
Good

### Findings
None

### Verdict
invalid_verdict

*Reviewed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(invalid_pr_review, "pr_review")

        assert is_valid is False
        assert "approve" in error_msg or "request_changes" in error_msg or "comment" in error_msg

    def test_validate_pr_review_missing_footer(self):
        """PR review without footer should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_pr_review = """## PR Review

### Summary
Summary here

### Code Quality
Good

### Findings
None

### Verdict
approve
"""

        is_valid, error_msg = validate_response_format(invalid_pr_review, "pr_review")

        assert is_valid is False
        assert "Reviewed by AI Agent" in error_msg or "footer" in error_msg.lower()

    def test_validate_issue_analysis_format_valid(self):
        """Validate correct issue analysis format passes."""
        from api.webhooks.github.validation import validate_response_format

        valid_issue_analysis = """## Analysis

### Findings
- Finding 1
- Finding 2

### Recommendations
- Recommendation 1

*Analyzed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(valid_issue_analysis, "issue_analysis")

        assert is_valid is True
        assert error_msg == ""

    def test_validate_issue_analysis_missing_header(self):
        """Issue analysis without '## Analysis' header should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_issue_analysis = """### Findings
Some findings

### Recommendations
Some recommendations

*Analyzed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(invalid_issue_analysis, "issue_analysis")

        assert is_valid is False
        assert "Analysis" in error_msg

    def test_validate_issue_analysis_missing_findings(self):
        """Issue analysis without Findings section should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_issue_analysis = """## Analysis

### Recommendations
Some recommendations

*Analyzed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(invalid_issue_analysis, "issue_analysis")

        assert is_valid is False
        assert "Findings" in error_msg

    def test_validate_issue_analysis_missing_recommendations(self):
        """Issue analysis without Recommendations section should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_issue_analysis = """## Analysis

### Findings
Some findings

*Analyzed by AI Agent*
"""

        is_valid, error_msg = validate_response_format(invalid_issue_analysis, "issue_analysis")

        assert is_valid is False
        assert "Recommendations" in error_msg

    def test_validate_issue_analysis_missing_footer(self):
        """Issue analysis without footer should fail."""
        from api.webhooks.github.validation import validate_response_format

        invalid_issue_analysis = """## Analysis

### Findings
Some findings

### Recommendations
Some recommendations
"""

        is_valid, error_msg = validate_response_format(invalid_issue_analysis, "issue_analysis")

        assert is_valid is False
        assert "Analyzed by AI Agent" in error_msg or "footer" in error_msg.lower()
