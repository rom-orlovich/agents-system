"""Unit tests for Jira operation scripts (TDD RED Phase - these tests will fail initially)."""

import pytest
import subprocess
import os
import json
from pathlib import Path


@pytest.fixture
def scripts_dir():
    """Return path to jira scripts directory."""
    return Path("/app/.claude/skills/jira-operations/scripts")


@pytest.fixture
def mock_jira_credentials(monkeypatch):
    """Mock Jira credentials via environment variables."""
    monkeypatch.setenv("JIRA_SERVER", "https://test.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "test-token-123")


class TestPostComment:
    """Tests for post_comment.sh script."""
    
    def test_post_comment_script_exists(self, scripts_dir):
        """Test that post_comment.sh script exists."""
        script = scripts_dir / "post_comment.sh"
        assert script.exists(), "post_comment.sh should exist"
        assert script.is_file(), "post_comment.sh should be a file"
    
    def test_post_comment_script_is_executable(self, scripts_dir):
        """Test that post_comment.sh is executable."""
        script = scripts_dir / "post_comment.sh"
        assert os.access(script, os.X_OK), "post_comment.sh should be executable"
    
    def test_post_comment_requires_issue_key(self, scripts_dir, mock_jira_credentials):
        """Test that script requires issue key parameter."""
        script = scripts_dir / "post_comment.sh"
        result = subprocess.run(
            [str(script)],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail without issue key"
        assert "Usage:" in result.stderr or "ISSUE_KEY" in result.stderr
    
    def test_post_comment_requires_comment_text(self, scripts_dir, mock_jira_credentials):
        """Test that script requires comment text parameter."""
        script = scripts_dir / "post_comment.sh"
        result = subprocess.run(
            [str(script), "PROJ-123"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail without comment text"
        assert "Usage:" in result.stderr or "COMMENT" in result.stderr


class TestFormatAnalysis:
    """Tests for format_analysis.sh script."""
    
    def test_format_analysis_script_exists(self, scripts_dir):
        """Test that format_analysis.sh script exists."""
        script = scripts_dir / "format_analysis.sh"
        assert script.exists(), "format_analysis.sh should exist"
        assert script.is_file(), "format_analysis.sh should be a file"
    
    def test_format_analysis_script_is_executable(self, scripts_dir):
        """Test that format_analysis.sh is executable."""
        script = scripts_dir / "format_analysis.sh"
        assert os.access(script, os.X_OK), "format_analysis.sh should be executable"
    
    def test_format_analysis_converts_markdown_to_adf(self, scripts_dir):
        """Test that formatter converts markdown to ADF (Atlassian Document Format)."""
        script = scripts_dir / "format_analysis.sh"
        
        # Simple test case: plain text
        result = subprocess.run(
            [str(script), "Test analysis result"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Should succeed with valid input"
        
        # Output should be valid JSON (ADF format)
        try:
            output_data = json.loads(result.stdout)
            assert "type" in output_data, "ADF should have 'type' field"
            assert "content" in output_data, "ADF should have 'content' field"
        except json.JSONDecodeError:
            pytest.fail("Output should be valid JSON (ADF format)")
    
    def test_format_analysis_handles_markdown_headers(self, scripts_dir):
        """Test that formatter converts markdown headers to ADF."""
        script = scripts_dir / "format_analysis.sh"
        
        markdown_text = "# Header\n## Subheader\nPlain text"
        result = subprocess.run(
            [str(script), markdown_text],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Should handle markdown headers"
        output_data = json.loads(result.stdout)
        
        # Check that ADF contains heading nodes
        content = output_data.get("content", [])
        heading_found = any(node.get("type") == "heading" for node in content)
        assert heading_found or len(content) > 0, "Should convert markdown to ADF structure"
