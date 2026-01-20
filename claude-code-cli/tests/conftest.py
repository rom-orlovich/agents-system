"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_redis_queue():
    """Mock RedisQueue client."""
    queue = Mock()
    queue.push = AsyncMock()
    queue.pop = AsyncMock()
    queue.update_task_status = AsyncMock()
    queue.get_task_status = AsyncMock(return_value="PENDING")
    queue.get_sentry_repo_mapping = Mock(return_value="org/repo")
    queue.store_sentry_repo_mapping = AsyncMock()
    return queue


@pytest.fixture
def mock_database():
    """Mock Database client."""
    db = Mock()
    db.store_task = AsyncMock()
    db.get_task = AsyncMock()
    db.update_task = AsyncMock()
    return db


@pytest.fixture
def mock_git_utils():
    """Mock GitUtils for git operations."""
    git = Mock()
    git.clone_repository = AsyncMock(return_value={"status": "success", "path": "/tmp/repo"})
    git.create_branch = AsyncMock()
    git.commit_and_push = AsyncMock()
    git.get_repo_path = Mock(return_value="/tmp/repo")
    return git


@pytest.fixture
def mock_claude_runner():
    """Mock Claude CLI runner."""
    runner = Mock()
    runner.run_claude_streaming = AsyncMock(return_value="# Analysis\nTest analysis")
    runner.run_claude_json = AsyncMock(return_value={"status": "success"})
    runner.extract_pr_url = Mock(return_value="https://github.com/org/repo/pull/123")
    return runner


@pytest.fixture
def mock_github_client():
    """Mock GitHub client."""
    client = Mock()
    client.create_pr = AsyncMock(return_value="https://github.com/org/repo/pull/123")
    client.update_pr = AsyncMock()
    client.add_comment = AsyncMock()
    client.add_reaction = AsyncMock()
    client.search_code = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_slack_client():
    """Mock Slack client."""
    client = Mock()
    client.send_message = AsyncMock()
    client.send_approval_message = AsyncMock()
    client.reply_in_thread = AsyncMock()
    return client


@pytest.fixture
def mock_jira_client():
    """Mock Jira client."""
    client = Mock()
    client.get_issue = AsyncMock(return_value={"key": "PROJ-123", "fields": {}})
    client.update_issue = AsyncMock()
    client.add_comment = AsyncMock()
    client.transition_issue = AsyncMock()
    return client


@pytest.fixture
def sample_jira_task():
    """Sample JiraTask for testing."""
    from shared.models import JiraTask
    from shared.enums import TaskStatus

    return JiraTask(
        task_id="task-123",
        jira_issue_key="PROJ-123",
        action="fix",
        repository="org/repo",
        sentry_issue_id=None,
        description="Fix login bug",
        status=TaskStatus.DISCOVERING
    )


@pytest.fixture
def sample_sentry_task():
    """Sample SentryTask for testing."""
    from shared.models import SentryTask
    from shared.enums import TaskStatus

    return SentryTask(
        task_id="task-456",
        sentry_issue_id="SENTRY-789",
        description="TypeError in auth module",
        repository="org/repo",
        stack_trace="Traceback...",
        status=TaskStatus.DISCOVERING
    )


@pytest.fixture
def sample_github_task():
    """Sample GitHubTask for testing."""
    from shared.models import GitHubTask
    from shared.enums import TaskStatus

    return GitHubTask(
        task_id="task-789",
        repository="org/repo",
        pr_number=42,
        pr_url="https://github.com/org/repo/pull/42",
        action="approve",
        comment=None,
        status=TaskStatus.PENDING_APPROVAL
    )
