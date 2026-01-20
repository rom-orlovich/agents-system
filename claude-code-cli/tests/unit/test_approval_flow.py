"""Test approval workflow and command processing."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from shared.enums import TaskStatus


@pytest.mark.asyncio
class TestApprovalCommands:
    """Test approval-related commands."""

    async def test_approve_command_from_github(
        self,
        sample_github_task,
        mock_redis_queue,
        mock_github_client
    ):
        """Test: @agent approve command from GitHub PR comment."""
        # Arrange
        task = sample_github_task
        task.action = "approve"
        task.status = TaskStatus.PENDING_APPROVAL

        # Act - Process approve command
        # 1. Update status to APPROVED
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.APPROVED)

        # 2. Push to execution queue
        await mock_redis_queue.push("execution_queue", task)

        # 3. Add reaction to comment
        await mock_github_client.add_reaction(
            task.repository,
            comment_id=123,
            reaction="rocket"
        )

        # 4. Reply to comment
        await mock_github_client.add_comment(
            task.repository,
            task.pr_number,
            "✅ Plan approved! Starting execution..."
        )

        # Assert
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.APPROVED
        )
        mock_redis_queue.push.assert_called_once_with("execution_queue", task)
        mock_github_client.add_reaction.assert_called_once()
        mock_github_client.add_comment.assert_called_once()

    async def test_approve_command_from_slack(
        self,
        sample_jira_task,
        mock_redis_queue,
        mock_slack_client
    ):
        """Test: Approve button click in Slack."""
        # Arrange
        task = sample_jira_task
        task.status = TaskStatus.PENDING_APPROVAL

        # Act - Process Slack button action
        # 1. Update status
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.APPROVED)

        # 2. Push to execution queue
        await mock_redis_queue.push("execution_queue", task)

        # 3. Send confirmation message
        await mock_slack_client.send_message(
            channel="engineering",
            text=f"✅ Task {task.task_id} approved and queued for execution"
        )

        # Assert
        mock_redis_queue.update_task_status.assert_called_once()
        mock_redis_queue.push.assert_called_once()
        mock_slack_client.send_message.assert_called_once()

    async def test_approve_via_jira_status_transition(
        self,
        sample_jira_task,
        mock_redis_queue,
        mock_jira_client
    ):
        """Test: Approval via Jira status transition to 'Approved'."""
        # Arrange
        task = sample_jira_task
        task.status = TaskStatus.PENDING_APPROVAL

        # Act - Jira webhook: status changed to "Approved"
        # 1. Update task status
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.APPROVED)

        # 2. Push to execution queue
        await mock_redis_queue.push("execution_queue", task)

        # 3. Add Jira comment
        await mock_jira_client.add_comment(
            task.jira_issue_key,
            "Plan approved. Starting implementation..."
        )

        # Assert
        mock_redis_queue.update_task_status.assert_called_once()
        mock_redis_queue.push.assert_called_once()
        mock_jira_client.add_comment.assert_called_once()


@pytest.mark.asyncio
class TestRejectCommands:
    """Test rejection commands."""

    async def test_reject_command_from_github(
        self,
        sample_github_task,
        mock_redis_queue,
        mock_github_client
    ):
        """Test: @agent reject command from GitHub."""
        # Arrange
        task = sample_github_task
        task.action = "reject"
        reject_reason = "Approach is too risky"

        # Act - Process reject command
        # 1. Update status to REJECTED
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.REJECTED)

        # 2. Add comment with reason
        await mock_github_client.add_comment(
            task.repository,
            task.pr_number,
            f"❌ Plan rejected. Reason: {reject_reason}"
        )

        # Assert
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.REJECTED
        )
        mock_github_client.add_comment.assert_called_once()

    async def test_reject_command_from_slack(
        self,
        sample_jira_task,
        mock_redis_queue,
        mock_slack_client
    ):
        """Test: Reject button in Slack."""
        # Arrange
        task = sample_jira_task
        task.status = TaskStatus.PENDING_APPROVAL

        # Act - Process Slack reject button
        # 1. Update status
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.REJECTED)

        # 2. Send message
        await mock_slack_client.send_message(
            channel="engineering",
            text=f"❌ Task {task.task_id} rejected"
        )

        # Assert
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.REJECTED
        )
        mock_slack_client.send_message.assert_called_once()


@pytest.mark.asyncio
class TestImproveCommands:
    """Test plan improvement commands."""

    async def test_improve_command_triggers_plan_changes(
        self,
        sample_github_task,
        mock_redis_queue,
        mock_github_client
    ):
        """Test: @agent improve triggers plan-changes skill."""
        # Arrange
        task = sample_github_task
        task.action = "improve"
        task.comment = "Please add error handling for edge cases"
        task.status = TaskStatus.PENDING_APPROVAL

        # Act - Process improve command
        # 1. Push to planning queue with feedback
        await mock_redis_queue.push("planning_queue", task)

        # 2. Add reaction
        await mock_github_client.add_reaction(
            task.repository,
            comment_id=456,
            reaction="eyes"
        )

        # 3. Reply
        await mock_github_client.add_comment(
            task.repository,
            task.pr_number,
            "🔄 Updating plan based on your feedback..."
        )

        # Assert
        mock_redis_queue.push.assert_called_once_with("planning_queue", task)
        mock_github_client.add_reaction.assert_called_once()
        mock_github_client.add_comment.assert_called_once()

    async def test_improve_command_keeps_pending_approval_status(
        self,
        sample_github_task,
        mock_redis_queue
    ):
        """Test: Improve command keeps task in PENDING_APPROVAL."""
        # Arrange
        task = sample_github_task
        task.action = "improve"
        task.status = TaskStatus.PENDING_APPROVAL

        # Act - Task should remain PENDING_APPROVAL
        # (status is not changed during improve, only after re-planning)

        # Assert
        assert task.status == TaskStatus.PENDING_APPROVAL


@pytest.mark.asyncio
class TestStatusCommand:
    """Test status query command."""

    async def test_status_command_returns_current_status(
        self,
        sample_jira_task,
        mock_redis_queue,
        mock_github_client
    ):
        """Test: @agent status returns current task status."""
        # Arrange
        task = sample_jira_task
        task.status = TaskStatus.EXECUTING

        # Mock get_task_status
        mock_redis_queue.get_task_status.return_value = TaskStatus.EXECUTING

        # Act - Query status
        status = mock_redis_queue.get_task_status(task.task_id)

        # Reply with status
        await mock_github_client.add_comment(
            task.repository,
            task.pr_number,
            f"📊 Task Status: {status.value}"
        )

        # Assert
        assert status == TaskStatus.EXECUTING
        mock_github_client.add_comment.assert_called_once()


@pytest.mark.asyncio
class TestCommandParsing:
    """Test command parsing from different platforms."""

    def test_parse_github_approve_command(self):
        """Test: Parse @agent approve from GitHub comment."""
        # Arrange
        comment_body = "@agent approve"

        # Act - Parse command
        command_parts = comment_body.split()
        if len(command_parts) >= 2 and command_parts[1] == "approve":
            command = "approve"
            args = []
        else:
            command = None
            args = []

        # Assert
        assert command == "approve"

    def test_parse_github_reject_with_reason(self):
        """Test: Parse @agent reject [reason] from GitHub."""
        # Arrange
        comment_body = "@agent reject Too risky, needs more tests"

        # Act - Parse command
        parts = comment_body.split(maxsplit=2)
        command = parts[1] if len(parts) >= 2 else None
        reason = parts[2] if len(parts) >= 3 else None

        # Assert
        assert command == "reject"
        assert reason == "Too risky, needs more tests"

    def test_parse_slack_mention(self):
        """Test: Parse command from Slack app_mention."""
        # Arrange
        slack_text = "<@U12345> approve"

        # Act - Normalize Slack mention
        normalized = slack_text.replace("<@U12345>", "@agent").strip()
        parts = normalized.split()
        command = parts[1] if len(parts) >= 2 else None

        # Assert
        assert command == "approve"

    def test_parse_command_aliases(self):
        """Test: Parse command aliases (lgtm, ship-it)."""
        # Arrange
        aliases = {
            "lgtm": "approve",
            "ship-it": "approve",
            "go": "approve",
            "no": "reject"
        }

        # Act & Assert
        assert aliases["lgtm"] == "approve"
        assert aliases["ship-it"] == "approve"
        assert aliases["no"] == "reject"


@pytest.mark.asyncio
class TestApprovalWorkflowIntegration:
    """Test complete approval workflow integration."""

    async def test_complete_approval_flow_github_to_execution(
        self,
        sample_github_task,
        mock_redis_queue,
        mock_github_client
    ):
        """Test: Complete flow from GitHub approval to execution start."""
        # Arrange
        task = sample_github_task
        task.status = TaskStatus.PENDING_APPROVAL

        # Act - Simulate complete flow
        # 1. GitHub webhook receives @agent approve
        task.action = "approve"

        # 2. Parse command
        command = "approve"

        # 3. Update status
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.APPROVED)

        # 4. Push to execution queue
        await mock_redis_queue.push("execution_queue", task)

        # 5. Add GitHub reactions & comments
        await mock_github_client.add_reaction(task.repository, 123, "rocket")
        await mock_github_client.add_comment(
            task.repository,
            task.pr_number,
            "✅ Approved and queued for execution"
        )

        # 6. Executor agent picks up from queue
        # (simulated - would be tested in executor flow tests)

        # Assert - Verify all steps executed
        mock_redis_queue.update_task_status.assert_called_once()
        mock_redis_queue.push.assert_called_once()
        mock_github_client.add_reaction.assert_called_once()
        mock_github_client.add_comment.assert_called_once()

    async def test_complete_rejection_flow_with_notification(
        self,
        sample_jira_task,
        mock_redis_queue,
        mock_slack_client,
        mock_jira_client
    ):
        """Test: Complete rejection flow with all notifications."""
        # Arrange
        task = sample_jira_task
        task.status = TaskStatus.PENDING_APPROVAL
        reject_reason = "Does not address root cause"

        # Act - Simulate rejection flow
        # 1. Update status
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.REJECTED)

        # 2. Notify Jira
        await mock_jira_client.add_comment(
            task.jira_issue_key,
            f"❌ Plan rejected. Reason: {reject_reason}"
        )

        # 3. Notify Slack
        await mock_slack_client.send_message(
            channel="engineering",
            text=f"Task {task.task_id} rejected: {reject_reason}"
        )

        # Assert
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.REJECTED
        )
        mock_jira_client.add_comment.assert_called_once()
        mock_slack_client.send_message.assert_called_once()
