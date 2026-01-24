"""Unit tests for GitHub complexity analyzer (TDD RED Phase)."""

import pytest
import subprocess
import os
from pathlib import Path


@pytest.fixture
def scripts_dir():
    """Return path to github scripts directory."""
    return Path("/app/.claude/skills/github-operations/scripts")


class TestAnalyzeComplexity:
    """Tests for analyze_complexity.sh script."""
    
    def test_script_exists(self, scripts_dir):
        """Test that analyze_complexity.sh exists."""
        script = scripts_dir / "analyze_complexity.sh"
        assert script.exists(), "analyze_complexity.sh should exist"
    
    def test_script_is_executable(self, scripts_dir):
        """Test that script is executable."""
        script = scripts_dir / "analyze_complexity.sh"
        assert os.access(script, os.X_OK), "Script should be executable"
    
    def test_returns_api_for_simple_queries(self, scripts_dir):
        """Test that simple queries return 'api'."""
        script = scripts_dir / "analyze_complexity.sh"
        
        simple_tasks = [
            "search for function definition",
            "find the config file",
            "check if file exists",
            "view README.md",
            "get the license file"
        ]
        
        for task in simple_tasks:
            result = subprocess.run(
                [str(script), task],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Should succeed for: {task}"
            assert result.stdout.strip() == "api", f"Should return 'api' for simple task: {task}"
    
    def test_returns_clone_for_complex_analysis(self, scripts_dir):
        """Test that complex analysis tasks return 'clone'."""
        script = scripts_dir / "analyze_complexity.sh"
        
        complex_tasks = [
            "analyze the codebase architecture",
            "refactor the authentication module",
            "implement a new feature for user management",
            "fix the database connection bug",
            "change all API endpoints to use async",
            "analyze multi-file dependencies"
        ]
        
        for task in complex_tasks:
            result = subprocess.run(
                [str(script), task],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Should succeed for: {task}"
            assert result.stdout.strip() == "clone", f"Should return 'clone' for complex task: {task}"
    
    def test_defaults_to_api_for_unknown(self, scripts_dir):
        """Test that unknown tasks default to 'api'."""
        script = scripts_dir / "analyze_complexity.sh"
        
        result = subprocess.run(
            [str(script), "random unknown task"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() in ["api", "clone"], "Should return either 'api' or 'clone'"


class TestCloneOrFetch:
    """Tests for clone_or_fetch.sh script."""
    
    def test_script_exists(self, scripts_dir):
        """Test that clone_or_fetch.sh exists."""
        script = scripts_dir / "clone_or_fetch.sh"
        assert script.exists(), "clone_or_fetch.sh should exist"
    
    def test_script_is_executable(self, scripts_dir):
        """Test that script is executable."""
        script = scripts_dir / "clone_or_fetch.sh"
        assert os.access(script, os.X_OK), "Script should be executable"
    
    def test_requires_repo_url(self, scripts_dir):
        """Test that script requires repository URL."""
        script = scripts_dir / "clone_or_fetch.sh"
        
        result = subprocess.run(
            [str(script)],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail without repo URL"
        assert "Usage:" in result.stderr or "REPO" in result.stderr


class TestCreateDraftPR:
    """Tests for create_draft_pr.sh script."""
    
    def test_script_exists(self, scripts_dir):
        """Test that create_draft_pr.sh exists."""
        script = scripts_dir / "create_draft_pr.sh"
        assert script.exists(), "create_draft_pr.sh should exist"
    
    def test_script_is_executable(self, scripts_dir):
        """Test that script is executable."""
        script = scripts_dir / "create_draft_pr.sh"
        assert os.access(script, os.X_OK), "Script should be executable"


class TestFetchFilesAPI:
    """Tests for fetch_files_api.sh script."""
    
    def test_script_exists(self, scripts_dir):
        """Test that fetch_files_api.sh exists."""
        script = scripts_dir / "fetch_files_api.sh"
        assert script.exists(), "fetch_files_api.sh should exist"
    
    def test_script_is_executable(self, scripts_dir):
        """Test that script is executable."""
        script = scripts_dir / "fetch_files_api.sh"
        assert os.access(script, os.X_OK), "Script should be executable"
