"""Unit tests for response format validation script."""

import subprocess
import pytest
from pathlib import Path


def run_format_validation(format_type: str, response_text: str) -> tuple[int, str, str]:
    """
    Run the validate-response-format.sh script with given format type and response.
    
    Returns:
        (exit_code, stdout, stderr)
    """
    script_path = Path(__file__).parent.parent.parent / "scripts" / "validate-response-format.sh"
    
    if not script_path.exists():
        pytest.skip(f"Validation script not found at {script_path}")
    
    # Format: "FORMAT_TYPE\nRESPONSE_TEXT"
    input_text = f"{format_type}\n{response_text}"
    
    result = subprocess.run(
        [str(script_path)],
        input=input_text,
        text=True,
        capture_output=True,
        timeout=5
    )
    
    return result.returncode, result.stdout, result.stderr


class TestPRReviewFormat:
    """Test PR review format validation."""
    
    def test_valid_pr_review_format_passes(self):
        """Valid PR review format should pass validation."""
        response = """## PR Review

### Summary
This PR adds a new feature for user authentication.

### Code Quality
The code is well-structured and follows best practices.

### Findings

#### Issues
- None found

#### Suggestions
- Consider adding more tests

### Files Reviewed
- auth.py
- login.py

### Verdict
approve

---
*Reviewed by AI Agent*"""
        
        exit_code, stdout, stderr = run_format_validation("pr_review", response)
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}. stderr: {stderr}"
    
    def test_pr_review_missing_summary_rejected(self):
        """PR review missing Summary section should be rejected."""
        response = """## PR Review

### Code Quality
Good

### Findings
None

### Verdict
approve

---
*Reviewed by AI Agent*"""
        
        exit_code, stdout, stderr = run_format_validation("pr_review", response)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"
        assert "Summary" in stderr
    
    def test_pr_review_missing_footer_rejected(self):
        """PR review missing footer should be rejected."""
        response = """## PR Review

### Summary
Good

### Code Quality
Good

### Findings
None

### Verdict
approve"""
        
        exit_code, stdout, stderr = run_format_validation("pr_review", response)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"


class TestIssueAnalysisFormat:
    """Test issue analysis format validation."""
    
    def test_valid_issue_analysis_format_passes(self):
        """Valid issue analysis format should pass validation."""
        response = """## Analysis

This issue describes a bug in the authentication system.

### Findings
- Bug found in login.py line 45
- Memory leak detected

### Relevant Code
`login.py:45`
```python
def login():
    # Bug here
    pass
```

### Recommendations
- Fix the bug
- Add tests

---
*Analyzed by AI Agent*"""
        
        exit_code, stdout, stderr = run_format_validation("issue_analysis", response)
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}. stderr: {stderr}"
    
    def test_issue_analysis_missing_findings_rejected(self):
        """Issue analysis missing Findings section should be rejected."""
        response = """## Analysis

Summary here.

### Recommendations
Fix it.

---
*Analyzed by AI Agent*"""
        
        exit_code, stdout, stderr = run_format_validation("issue_analysis", response)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"
        assert "Findings" in stderr


class TestJiraFormat:
    """Test Jira ADF format validation."""
    
    def test_valid_jira_adf_format_passes(self):
        """Valid Jira ADF format should pass validation."""
        response = """{
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analysis complete"
                        }
                    ]
                }
            ]
        }"""
        
        exit_code, stdout, stderr = run_format_validation("jira", response)
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}. stderr: {stderr}"
    
    def test_jira_invalid_json_rejected(self):
        """Invalid JSON should be rejected."""
        response = "This is not JSON"
        
        exit_code, stdout, stderr = run_format_validation("jira", response)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"


class TestSlackFormat:
    """Test Slack format validation."""
    
    def test_valid_slack_format_passes(self):
        """Valid Slack format should pass validation."""
        response = "This is a Slack message with *bold* and `code` formatting."
        
        exit_code, stdout, stderr = run_format_validation("slack", response)
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}. stderr: {stderr}"
    
    def test_slack_too_long_rejected(self):
        """Slack message exceeding 4000 characters should be rejected."""
        response = "x" * 4001  # 4001 characters
        
        exit_code, stdout, stderr = run_format_validation("slack", response)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"
        assert "4000" in stderr
    
    def test_slack_empty_rejected(self):
        """Empty Slack message should be rejected."""
        response = ""
        
        exit_code, stdout, stderr = run_format_validation("slack", response)
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stdout: {stdout}"
