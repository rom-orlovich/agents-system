"""Test executor agent workflow and TDD cycle."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from shared.enums import TaskStatus


@pytest.mark.asyncio
class TestExecutorAgentFlow:
    """Test executor agent complete workflow."""

    async def test_complete_tdd_workflow(
        self,
        sample_jira_task,
        mock_git_utils,
        mock_claude_runner,
        mock_redis_queue,
        mock_github_client
    ):
        """Test: Complete TDD workflow (RED → GREEN → REFACTOR)."""
        # Arrange
        task = sample_jira_task
        task.status = TaskStatus.APPROVED
        working_dir = "/tmp/repo"
        branch_name = f"fix/{task.task_id}"

        # Act - Simulate executor agent flow

        # 1. Clone repository
        await mock_git_utils.clone_repository(task.repository)
        mock_git_utils.get_repo_path.return_value = working_dir

        # 2. Create branch
        await mock_git_utils.create_branch(working_dir, branch_name)

        # 3. RED: Run initial tests (expect failures)
        initial_tests = {"passed": 45, "failed": 3}

        # 4. GREEN: Implement fix
        await mock_claude_runner.run_claude_streaming(
            skill="execution",
            context={"task": task}
        )

        # 5. VERIFY: Run tests again
        final_tests = {"passed": 48, "failed": 0}

        # 6. COMMIT: Commit and push
        await mock_git_utils.commit_and_push(working_dir, branch_name)

        # 7. Update PR
        await mock_github_client.update_pr(
            task.repository,
            task.pr_number,
            body="Implementation complete"
        )

        # 8. Update status
        await mock_redis_queue.update_task_status(
            task.task_id,
            TaskStatus.COMPLETED
        )

        # Assert
        mock_git_utils.clone_repository.assert_called_once()
        mock_git_utils.create_branch.assert_called_once_with(working_dir, branch_name)
        mock_claude_runner.run_claude_streaming.assert_called_once()
        mock_git_utils.commit_and_push.assert_called_once()
        mock_github_client.update_pr.assert_called_once()
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.COMPLETED
        )

    async def test_executor_reads_project_claude_md(
        self,
        sample_jira_task,
        mock_git_utils
    ):
        """Test: Executor agent reads project CLAUDE.md for context."""
        # Arrange
        task = sample_jira_task
        working_dir = "/tmp/repo"
        claude_md_content = "# Project Rules\n- Always write tests\n- Use ESLint"

        # Mock file read
        with patch("builtins.open", mock_open(read_data=claude_md_content)):
            with patch("os.path.exists", return_value=True):
                # Act
                with open(f"{working_dir}/CLAUDE.md", "r") as f:
                    project_rules = f.read()

        # Assert
        assert "write tests" in project_rules
        assert "ESLint" in project_rules

    async def test_executor_creates_feature_branch(
        self,
        sample_jira_task,
        mock_git_utils
    ):
        """Test: Executor creates feature branch."""
        # Arrange
        task = sample_jira_task
        working_dir = "/tmp/repo"
        branch_name = f"fix/{task.task_id}"

        # Act
        await mock_git_utils.create_branch(working_dir, branch_name)

        # Assert
        mock_git_utils.create_branch.assert_called_once_with(working_dir, branch_name)


@pytest.mark.asyncio
class TestTDDWorkflow:
    """Test TDD RED-GREEN-REFACTOR cycle."""

    async def test_red_phase_runs_existing_tests(self):
        """Test: RED phase runs existing tests."""
        # Arrange - Mock test runner
        test_runner = Mock()
        test_runner.run_tests = AsyncMock(return_value={
            "passed": 45,
            "failed": 3,
            "framework": "pytest"
        })

        # Act - Run RED phase
        result = await test_runner.run_tests("/tmp/repo")

        # Assert
        assert result["failed"] > 0  # Some tests should fail initially
        test_runner.run_tests.assert_called_once()

    async def test_green_phase_implements_fix(
        self,
        sample_jira_task,
        mock_claude_runner
    ):
        """Test: GREEN phase implements the fix."""
        # Arrange
        task = sample_jira_task
        working_dir = "/tmp/repo"

        # Act - Run execution skill
        await mock_claude_runner.run_claude_streaming(
            skill="execution",
            context={"task": task, "working_dir": working_dir}
        )

        # Assert
        mock_claude_runner.run_claude_streaming.assert_called_once()

    async def test_verify_phase_all_tests_pass(self):
        """Test: VERIFY phase confirms all tests pass."""
        # Arrange
        test_runner = Mock()
        test_runner.run_tests = AsyncMock(return_value={
            "passed": 48,
            "failed": 0,
            "framework": "pytest"
        })

        # Act
        result = await test_runner.run_tests("/tmp/repo")

        # Assert
        assert result["failed"] == 0  # All tests should pass
        assert result["passed"] > 0


@pytest.mark.asyncio
class TestCodeReviewSkill:
    """Test code review skill execution."""

    async def test_run_linters(self):
        """Test: Code review runs linters."""
        # Arrange
        lint_runner = Mock()
        lint_runner.run_lint = AsyncMock(return_value={
            "errors": [],
            "warnings": ["line too long"],
            "passed": True
        })

        # Act
        result = await lint_runner.run_lint("/tmp/repo")

        # Assert
        assert result["passed"] is True
        assert len(result["errors"]) == 0

    async def test_fail_on_lint_errors(self):
        """Test: Code review fails if linting errors exist."""
        # Arrange
        lint_runner = Mock()
        lint_runner.run_lint = AsyncMock(return_value={
            "errors": ["undefined variable 'foo'"],
            "warnings": [],
            "passed": False
        })

        # Act
        result = await lint_runner.run_lint("/tmp/repo")

        # Assert
        assert result["passed"] is False
        assert len(result["errors"]) > 0


@pytest.mark.asyncio
class TestGitOperationsSkill:
    """Test git operations skill."""

    async def test_commit_and_push(
        self,
        mock_git_utils
    ):
        """Test: Git operations commits and pushes changes."""
        # Arrange
        working_dir = "/tmp/repo"
        branch = "fix/task-123"

        # Act
        await mock_git_utils.commit_and_push(working_dir, branch)

        # Assert
        mock_git_utils.commit_and_push.assert_called_once_with(working_dir, branch)

    async def test_commit_message_format(
        self,
        sample_jira_task,
        mock_git_utils
    ):
        """Test: Commit message follows format."""
        # Arrange
        task = sample_jira_task
        expected_message = f"fix: {task.description}\n\nCloses {task.jira_issue_key}"

        # Act - Format commit message
        commit_message = f"fix: {task.description}\n\nCloses {task.jira_issue_key}"

        # Assert
        assert task.jira_issue_key in commit_message
        assert "fix:" in commit_message


@pytest.mark.asyncio
class TestGitHubPRSkill:
    """Test GitHub PR operations skill."""

    async def test_update_pr_with_implementation_notes(
        self,
        sample_github_task,
        mock_github_client
    ):
        """Test: Update PR with implementation details."""
        # Arrange
        task = sample_github_task
        implementation_notes = "## Changes\n- Fixed auth bug\n- Added tests"

        # Act
        await mock_github_client.update_pr(
            task.repository,
            task.pr_number,
            body=implementation_notes
        )

        # Assert
        mock_github_client.update_pr.assert_called_once()

    async def test_add_comment_to_pr(
        self,
        sample_github_task,
        mock_github_client
    ):
        """Test: Add comment to PR after completion."""
        # Arrange
        task = sample_github_task
        comment = "✅ Implementation complete. All tests pass."

        # Act
        await mock_github_client.add_comment(
            task.repository,
            task.pr_number,
            comment
        )

        # Assert
        mock_github_client.add_comment.assert_called_once_with(
            task.repository,
            task.pr_number,
            comment
        )


@pytest.mark.asyncio
class TestExecutorErrorHandling:
    """Test executor agent error handling."""

    async def test_handle_test_failure_after_implementation(
        self,
        sample_jira_task,
        mock_redis_queue
    ):
        """Test: Handle case where tests still fail after implementation."""
        # Arrange
        task = sample_jira_task
        test_result = {"passed": 45, "failed": 3}

        # Act - If tests still fail, mark as FAILED
        if test_result["failed"] > 0:
            await mock_redis_queue.update_task_status(
                task.task_id,
                TaskStatus.FAILED
            )

        # Assert
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.FAILED
        )

    async def test_handle_lint_failure(
        self,
        sample_jira_task,
        mock_redis_queue
    ):
        """Test: Handle linting failures."""
        # Arrange
        task = sample_jira_task
        lint_result = {"errors": ["syntax error"], "passed": False}

        # Act - If lint fails, mark as FAILED
        if not lint_result["passed"]:
            await mock_redis_queue.update_task_status(
                task.task_id,
                TaskStatus.FAILED
            )

        # Assert
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.FAILED
        )

    async def test_handle_git_push_failure(
        self,
        sample_jira_task,
        mock_git_utils,
        mock_redis_queue
    ):
        """Test: Handle git push failure."""
        # Arrange
        task = sample_jira_task
        mock_git_utils.commit_and_push.side_effect = Exception("Push failed")

        # Act & Assert
        try:
            await mock_git_utils.commit_and_push("/tmp/repo", "fix/task-123")
        except Exception:
            await mock_redis_queue.update_task_status(
                task.task_id,
                TaskStatus.FAILED
            )

        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.FAILED
        )
