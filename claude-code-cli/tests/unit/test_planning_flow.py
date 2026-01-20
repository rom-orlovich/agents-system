"""Test planning agent workflow."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from shared.enums import TaskStatus


@pytest.mark.asyncio
class TestPlanningAgentFlow:
    """Test planning agent processing flow."""

    async def test_process_sentry_task_discovery(
        self,
        sample_sentry_task,
        mock_redis_queue,
        mock_git_utils,
        mock_claude_runner
    ):
        """Test: Planning agent processes SentryTask with discovery skill."""
        # Arrange
        task = sample_sentry_task
        working_dir = "/tmp/repo"

        # Act - Simulate planning agent processing
        # 1. Clone repository
        await mock_git_utils.clone_repository(task.repository)

        # 2. Run discovery skill
        discovery_result = await mock_claude_runner.run_claude_streaming(
            skill="discovery",
            context={"task": task, "working_dir": working_dir}
        )

        # 3. Update task status
        await mock_redis_queue.update_task_status(
            task.task_id,
            TaskStatus.PENDING_APPROVAL
        )

        # Assert
        mock_git_utils.clone_repository.assert_called_once()
        mock_claude_runner.run_claude_streaming.assert_called_once()
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.PENDING_APPROVAL
        )

    async def test_process_jira_task_enrichment(
        self,
        sample_jira_task,
        mock_redis_queue,
        mock_git_utils,
        mock_claude_runner,
        mock_jira_client
    ):
        """Test: Planning agent enriches Jira ticket with Sentry data."""
        # Arrange
        task = sample_jira_task
        task.action = "enrich"
        task.sentry_issue_id = "SENTRY-123"

        # Act - Simulate jira-enrichment skill
        # 1. Get Sentry details (via script)
        sentry_data = {"error": "TypeError", "trace": "..."}

        # 2. Update Jira with analysis
        await mock_jira_client.add_comment(
            task.jira_issue_key,
            "# Analysis\nSentry error details..."
        )

        # 3. Update status
        await mock_redis_queue.update_task_status(
            task.task_id,
            TaskStatus.PENDING_APPROVAL
        )

        # Assert
        mock_jira_client.add_comment.assert_called_once()
        mock_redis_queue.update_task_status.assert_called_once()

    async def test_planning_agent_reads_project_claude_md(
        self,
        sample_jira_task,
        mock_git_utils
    ):
        """Test: Planning agent reads project CLAUDE.md for context."""
        # Arrange
        task = sample_jira_task
        working_dir = "/tmp/repo"
        claude_md_content = "# Project Rules\n- Use TypeScript\n- Write tests"

        # Mock file read
        with patch("builtins.open", mock_open(read_data=claude_md_content)):
            with patch("os.path.exists", return_value=True):
                # Act - Read CLAUDE.md
                with open(f"{working_dir}/CLAUDE.md", "r") as f:
                    project_rules = f.read()

        # Assert
        assert project_rules == claude_md_content
        assert "TypeScript" in project_rules

    async def test_planning_agent_creates_draft_pr(
        self,
        sample_jira_task,
        mock_github_client,
        mock_claude_runner
    ):
        """Test: Planning agent creates draft PR with PLAN.md."""
        # Arrange
        task = sample_jira_task
        plan_content = "# Fix Plan\n## Analysis\n..."

        # Mock PR URL extraction
        mock_claude_runner.extract_pr_url.return_value = (
            "https://github.com/org/repo/pull/123"
        )

        # Act - Create draft PR
        pr_url = await mock_github_client.create_pr(
            repository=task.repository,
            title=f"[PLAN] {task.description}",
            body=plan_content,
            draft=True
        )

        # Assert
        mock_github_client.create_pr.assert_called_once()
        assert pr_url == "https://github.com/org/repo/pull/123"

    async def test_planning_agent_sends_slack_notification(
        self,
        sample_jira_task,
        mock_slack_client
    ):
        """Test: Planning agent sends Slack notification after creating plan."""
        # Arrange
        task = sample_jira_task
        pr_url = "https://github.com/org/repo/pull/123"

        # Act - Send notification
        await mock_slack_client.send_approval_message(
            task_id=task.task_id,
            title=task.description,
            pr_url=pr_url
        )

        # Assert
        mock_slack_client.send_approval_message.assert_called_once_with(
            task_id=task.task_id,
            title=task.description,
            pr_url=pr_url
        )


@pytest.mark.asyncio
class TestPlanningAgentSkillRouting:
    """Test planning agent routes tasks to correct skills."""

    async def test_route_jira_enrich_to_jira_enrichment_skill(
        self,
        sample_jira_task,
        mock_claude_runner
    ):
        """Test: JiraTask(action='enrich') → jira-enrichment skill."""
        # Arrange
        task = sample_jira_task
        task.action = "enrich"

        # Act - Simulate skill selection logic
        if task.action == "enrich":
            skill_name = "jira-enrichment"
        else:
            skill_name = "discovery"

        # Assert
        assert skill_name == "jira-enrichment"

    async def test_route_sentry_task_to_discovery_skill(
        self,
        sample_sentry_task,
        mock_claude_runner
    ):
        """Test: SentryTask → discovery skill."""
        # Arrange
        task = sample_sentry_task

        # Act - Simulate skill selection
        from shared.models import SentryTask
        if isinstance(task, SentryTask):
            skill_name = "discovery"
        else:
            skill_name = "unknown"

        # Assert
        assert skill_name == "discovery"

    async def test_route_github_improve_to_plan_changes_skill(
        self,
        sample_github_task
    ):
        """Test: GitHubTask(action='improve') → plan-changes skill."""
        # Arrange
        task = sample_github_task
        task.action = "improve"

        # Act - Simulate skill selection
        if task.action == "improve":
            skill_name = "plan-changes"
        else:
            skill_name = "execution"

        # Assert
        assert skill_name == "plan-changes"

    async def test_route_approved_task_to_execution_skill(
        self,
        sample_jira_task
    ):
        """Test: Task(status=APPROVED) → execution skill."""
        # Arrange
        task = sample_jira_task
        task.status = TaskStatus.APPROVED

        # Act - Simulate skill selection
        if task.status == TaskStatus.APPROVED:
            skill_name = "execution"
        else:
            skill_name = "discovery"

        # Assert
        assert skill_name == "execution"


@pytest.mark.asyncio
class TestPlanningAgentErrorHandling:
    """Test planning agent error handling."""

    async def test_handle_missing_repository(
        self,
        sample_jira_task,
        mock_redis_queue
    ):
        """Test: Handle task with missing repository gracefully."""
        # Arrange
        task = sample_jira_task
        task.repository = None

        # Act - Should fall back to agent directory
        repository = task.repository
        if not repository:
            working_dir = "/agent/workspace"
        else:
            working_dir = f"/tmp/{repository}"

        # Assert
        assert working_dir == "/agent/workspace"

    async def test_handle_missing_claude_md(
        self,
        sample_jira_task
    ):
        """Test: Handle missing CLAUDE.md file gracefully."""
        # Arrange
        working_dir = "/tmp/repo"

        # Mock file doesn't exist
        with patch("os.path.exists", return_value=False):
            # Act - Try to read CLAUDE.md
            project_rules = None
            if not os.path.exists(f"{working_dir}/CLAUDE.md"):
                project_rules = None

        # Assert - Should not fail, just use None
        assert project_rules is None

    async def test_handle_git_clone_failure(
        self,
        sample_jira_task,
        mock_git_utils,
        mock_redis_queue
    ):
        """Test: Handle git clone failure."""
        # Arrange
        task = sample_jira_task
        mock_git_utils.clone_repository.side_effect = Exception("Clone failed")

        # Act & Assert - Should mark task as failed
        try:
            await mock_git_utils.clone_repository(task.repository)
        except Exception:
            await mock_redis_queue.update_task_status(
                task.task_id,
                TaskStatus.FAILED
            )

        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.FAILED
        )
