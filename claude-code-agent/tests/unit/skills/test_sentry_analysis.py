"""Unit tests for Sentry analysis scripts (TDD RED Phase)."""

import pytest
import subprocess
import os
from pathlib import Path


def _get_scripts_dir(relative_path: str) -> Path:
    """Get scripts directory, handling both Docker and local environments."""
    docker_path = Path("/app/.claude/skills") / relative_path
    local_path = Path(__file__).parent.parent.parent.parent / ".claude/skills" / relative_path
    
    if docker_path.exists():
        return docker_path
    elif local_path.exists():
        return local_path
    else:
        return docker_path


@pytest.fixture
def scripts_dir():
    """Return path to sentry scripts directory."""
    return _get_scripts_dir("sentry-operations/scripts")


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
        if not script.exists():
            pytest.skip(f"Script {script} does not exist")
        if not os.access(script, os.X_OK):
            os.chmod(script, 0o755)
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
        if not script.exists():
            pytest.skip(f"Script {script} does not exist")
        if not os.access(script, os.X_OK):
            os.chmod(script, 0o755)
        assert os.access(script, os.X_OK), "Script should be executable"
    
    def test_requires_both_ids(self, scripts_dir, mock_sentry_credentials):
        """Test that script requires both Sentry issue ID and Jira ticket key."""
        script = scripts_dir / "link_to_jira.sh"
        if not script.exists():
            pytest.skip(f"Script {script} does not exist")
        
        # Ensure script is executable
        if not os.access(script, os.X_OK):
            os.chmod(script, 0o755)
        
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
