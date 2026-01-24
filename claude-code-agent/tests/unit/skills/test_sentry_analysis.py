"""Unit tests for Sentry analysis scripts (TDD RED Phase)."""

import pytest
import subprocess
import os
from pathlib import Path


@pytest.fixture
def scripts_dir():
    """Return path to sentry scripts directory."""
    return Path("/app/.claude/skills/sentry-operations/scripts")


@pytest.fixture
def mock_sentry_credentials(monkeypatch):
    """Mock Sentry credentials via environment variables."""
    monkeypatch.setenv("SENTRY_AUTH_TOKEN", "test-sentry-token")
    monkeypatch.setenv("SENTRY_ORG", "test-org")


class TestAnalyzeError:
    """Tests for analyze_error.sh script."""
    
    def test_script_exists(self, scripts_dir):
        """Test that analyze_error.sh exists."""
        script = scripts_dir / "analyze_error.sh"
        assert script.exists(), "analyze_error.sh should exist"
    
    def test_script_is_executable(self, scripts_dir):
        """Test that script is executable."""
        script = scripts_dir / "analyze_error.sh"
        assert os.access(script, os.X_OK), "Script should be executable"
    
    def test_requires_issue_id(self, scripts_dir, mock_sentry_credentials):
        """Test that script requires Sentry issue ID."""
        script = scripts_dir / "analyze_error.sh"
        
        result = subprocess.run(
            [str(script)],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail without issue ID"
        assert "Usage:" in result.stderr or "ISSUE_ID" in result.stderr


class TestLinkToJira:
    """Tests for link_to_jira.sh script."""
    
    def test_script_exists(self, scripts_dir):
        """Test that link_to_jira.sh exists."""
        script = scripts_dir / "link_to_jira.sh"
        assert script.exists(), "link_to_jira.sh should exist"
    
    def test_script_is_executable(self, scripts_dir):
        """Test that script is executable."""
        script = scripts_dir / "link_to_jira.sh"
        assert os.access(script, os.X_OK), "Script should be executable"
    
    def test_requires_both_ids(self, scripts_dir, mock_sentry_credentials):
        """Test that script requires both Sentry issue ID and Jira ticket key."""
        script = scripts_dir / "link_to_jira.sh"
        
        # Test with no arguments
        result = subprocess.run(
            [str(script)],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail without arguments"
        
        # Test with only one argument
        result = subprocess.run(
            [str(script), "sentry-123"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail with only one argument"
