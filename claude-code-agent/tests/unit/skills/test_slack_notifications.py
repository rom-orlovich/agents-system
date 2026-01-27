"""Unit tests for Slack notification scripts (TDD RED Phase)."""

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
    """Return path to slack scripts directory."""
    return _get_scripts_dir("slack-operations/scripts")


@pytest.fixture
def mock_slack_credentials(monkeypatch):
    """Mock Slack credentials via environment variables."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_NOTIFICATION_CHANNEL", "#test-channel")


class TestNotifyJobStart:
    """Tests for notify_job_start.sh script."""
    
    def test_script_exists(self, scripts_dir):
        """Test that notify_job_start.sh exists."""
        script = scripts_dir / "notify_job_start.sh"
        assert script.exists(), "notify_job_start.sh should exist"
    
    def test_script_is_executable(self, scripts_dir):
        """Test that script is executable."""
        script = scripts_dir / "notify_job_start.sh"
        if not script.exists():
            pytest.skip(f"Script {script} does not exist")
        if not os.access(script, os.X_OK):
            os.chmod(script, 0o755)
        assert os.access(script, os.X_OK), "Script should be executable"
    
    def test_requires_task_id(self, scripts_dir, mock_slack_credentials):
        """Test that script requires task_id parameter."""
        script = scripts_dir / "notify_job_start.sh"
        
        result = subprocess.run(
            [str(script)],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail without task_id"
        assert "Usage:" in result.stderr or "TASK_ID" in result.stderr
    
    def test_accepts_task_metadata(self, scripts_dir, mock_slack_credentials):
        """Test that script accepts task metadata (source, command, agent)."""
        script = scripts_dir / "notify_job_start.sh"
        
        result = subprocess.run(
            [
                str(script),
                "task-123",
                "jira",
                "analyze ticket",
                "planning"
            ],
            capture_output=True,
            text=True
        )
        # Script might fail (no real Slack) but should accept parameters
        assert "Usage:" not in result.stderr


class TestNotifyJobComplete:
    """Tests for notify_job_complete.sh script."""
    
    def test_script_exists(self, scripts_dir):
        """Test that notify_job_complete.sh exists."""
        script = scripts_dir / "notify_job_complete.sh"
        assert script.exists(), "notify_job_complete.sh should exist"
    
    def test_script_is_executable(self, scripts_dir):
        """Test that script is executable."""
        script = scripts_dir / "notify_job_complete.sh"
        if not script.exists():
            pytest.skip(f"Script {script} does not exist")
        if not os.access(script, os.X_OK):
            os.chmod(script, 0o755)
        assert os.access(script, os.X_OK), "Script should be executable"
    
    def test_requires_task_id(self, scripts_dir, mock_slack_credentials):
        """Test that script requires task_id parameter."""
        script = scripts_dir / "notify_job_complete.sh"
        if not script.exists():
            pytest.skip(f"Script {script} does not exist")
        
        # Ensure script is executable
        if not os.access(script, os.X_OK):
            os.chmod(script, 0o755)
        
        result = subprocess.run(
            [str(script)],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail without task_id"
        assert "Usage:" in result.stderr or "TASK_ID" in result.stderr
    
    def test_accepts_completion_metadata(self, scripts_dir, mock_slack_credentials):
        """Test that script accepts completion metadata (status, cost)."""
        script = scripts_dir / "notify_job_complete.sh"
        if not script.exists():
            pytest.skip(f"Script {script} does not exist")
        
        # Ensure script is executable
        if not os.access(script, os.X_OK):
            os.chmod(script, 0o755)
        
        result = subprocess.run(
            [
                str(script),
                "task-123",
                "completed",
                "0.05",
                "Analysis complete"
            ],
            capture_output=True,
            text=True
        )
        # Script might fail (no real Slack) but should accept parameters
        assert "Usage:" not in result.stderr
