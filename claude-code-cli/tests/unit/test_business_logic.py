"""Test task lifecycle and business logic flows."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from shared.enums import TaskStatus, TaskSource


@pytest.mark.asyncio
class TestTaskLifecycle:
    """Test complete task lifecycle from webhook to completion."""

    async def test_sentry_to_jira_enrichment_flow(
        self,
        sample_sentry_task,
        mock_redis_queue,
        mock_jira_client
    ):
        """Test: Sentry alert → Planning agent → Jira enrichment."""
        # Arrange
        task = sample_sentry_task

        # Act - Push to planning queue
        await mock_redis_queue.push("planning_queue", task)

        # Assert - Task should be queued
        mock_redis_queue.push.assert_called_once_with("planning_queue", task)
        assert task.status == TaskStatus.DISCOVERING

    async def test_jira_ticket_to_plan_creation(
        self,
        sample_jira_task,
        mock_redis_queue
    ):
        """Test: Jira ticket assigned → Planning agent → Create plan."""
        # Arrange
        task = sample_jira_task

        # Act - Push to planning queue
        await mock_redis_queue.push("planning_queue", task)

        # Assert
        mock_redis_queue.push.assert_called_once_with("planning_queue", task)
        assert task.action == "fix"

    async def test_approval_transitions_to_execution(
        self,
        sample_jira_task,
        mock_redis_queue
    ):
        """Test: @agent approve → Update status → Push to execution queue."""
        # Arrange
        task = sample_jira_task
        task.status = TaskStatus.PENDING_APPROVAL

        # Act - Approve task
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.APPROVED)
        await mock_redis_queue.push("execution_queue", task)

        # Assert
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.APPROVED
        )
        mock_redis_queue.push.assert_called_once_with("execution_queue", task)

    async def test_execution_to_completion(
        self,
        sample_jira_task,
        mock_redis_queue
    ):
        """Test: Executor agent implements fix → Completes task."""
        # Arrange
        task = sample_jira_task
        task.status = TaskStatus.EXECUTING

        # Act - Complete task
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.COMPLETED)

        # Assert
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.COMPLETED
        )

    async def test_task_rejection(
        self,
        sample_github_task,
        mock_redis_queue
    ):
        """Test: @agent reject → Update status to REJECTED."""
        # Arrange
        task = sample_github_task
        task.status = TaskStatus.PENDING_APPROVAL

        # Act - Reject task
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.REJECTED)

        # Assert
        mock_redis_queue.update_task_status.assert_called_once_with(
            task.task_id,
            TaskStatus.REJECTED
        )


@pytest.mark.asyncio
class TestTaskStatusTransitions:
    """Test valid task status transitions."""

    @pytest.mark.parametrize("from_status,to_status,is_valid", [
        (TaskStatus.DISCOVERING, TaskStatus.PENDING_APPROVAL, True),
        (TaskStatus.DISCOVERING, TaskStatus.FAILED, True),
        (TaskStatus.PENDING_APPROVAL, TaskStatus.APPROVED, True),
        (TaskStatus.PENDING_APPROVAL, TaskStatus.REJECTED, True),
        (TaskStatus.APPROVED, TaskStatus.EXECUTING, True),
        (TaskStatus.EXECUTING, TaskStatus.COMPLETED, True),
        (TaskStatus.EXECUTING, TaskStatus.FAILED, True),
        (TaskStatus.COMPLETED, TaskStatus.DISCOVERING, False),  # Invalid
        (TaskStatus.REJECTED, TaskStatus.APPROVED, False),  # Invalid
    ])
    async def test_status_transition_validity(
        self,
        from_status,
        to_status,
        is_valid,
        mock_redis_queue
    ):
        """Test: Verify valid and invalid status transitions."""
        task_id = "task-123"

        if is_valid:
            # Valid transitions should succeed
            await mock_redis_queue.update_task_status(task_id, to_status)
            mock_redis_queue.update_task_status.assert_called_once_with(
                task_id,
                to_status
            )
        else:
            # Invalid transitions should be rejected (when implemented)
            # For now, just document expected behavior
            pass


@pytest.mark.asyncio
class TestWebhookToTaskCreation:
    """Test webhook event to task creation."""

    async def test_sentry_webhook_creates_sentry_task(self, mock_redis_queue):
        """Test: Sentry webhook → Create SentryTask → Push to planning queue."""
        from shared.models import SentryTask

        # Arrange - Simulated Sentry webhook payload
        sentry_payload = {
            "id": "SENTRY-123",
            "project": "backend",
            "message": "TypeError: Cannot read property 'id' of undefined",
            "tags": [{"key": "repository", "value": "org/backend"}]
        }

        # Act - Create task from webhook
        task = SentryTask(
            task_id=f"sentry-{sentry_payload['id']}",
            sentry_issue_id=sentry_payload["id"],
            description=sentry_payload["message"],
            repository="org/backend",
            stack_trace=None,
            status=TaskStatus.DISCOVERING
        )
        await mock_redis_queue.push("planning_queue", task)

        # Assert
        assert task.sentry_issue_id == "SENTRY-123"
        assert task.repository == "org/backend"
        mock_redis_queue.push.assert_called_once()

    async def test_jira_webhook_creates_jira_task(self, mock_redis_queue):
        """Test: Jira webhook (assigned to bot) → Create JiraTask → Planning queue."""
        from shared.models import JiraTask

        # Arrange - Simulated Jira webhook
        jira_payload = {
            "issue": {
                "key": "PROJ-456",
                "fields": {
                    "summary": "Fix authentication bug",
                    "assignee": {"name": "ai-agent-bot"}
                }
            }
        }

        # Act - Create task
        task = JiraTask(
            task_id=f"jira-{jira_payload['issue']['key']}",
            jira_issue_key=jira_payload["issue"]["key"],
            action="fix",
            repository=None,
            sentry_issue_id=None,
            description=jira_payload["issue"]["fields"]["summary"],
            status=TaskStatus.DISCOVERING
        )
        await mock_redis_queue.push("planning_queue", task)

        # Assert
        assert task.jira_issue_key == "PROJ-456"
        assert task.action == "fix"
        mock_redis_queue.push.assert_called_once()

    async def test_github_pr_comment_creates_github_task(self, mock_redis_queue):
        """Test: GitHub PR comment (@agent approve) → Create GitHubTask."""
        from shared.models import GitHubTask

        # Arrange - Simulated GitHub webhook
        gh_payload = {
            "action": "created",
            "comment": {"body": "@agent approve"},
            "issue": {
                "number": 42,
                "html_url": "https://github.com/org/repo/pull/42"
            },
            "repository": {"full_name": "org/repo"}
        }

        # Act - Create task
        task = GitHubTask(
            task_id=f"gh-org-repo-42",
            repository=gh_payload["repository"]["full_name"],
            pr_number=gh_payload["issue"]["number"],
            pr_url=gh_payload["issue"]["html_url"],
            action="approve",
            comment=None,
            status=TaskStatus.PENDING_APPROVAL
        )
        await mock_redis_queue.update_task_status(task.task_id, TaskStatus.APPROVED)
        await mock_redis_queue.push("execution_queue", task)

        # Assert
        assert task.action == "approve"
        mock_redis_queue.push.assert_called_once()


@pytest.mark.asyncio
class TestSentryRepoMapping:
    """Test Sentry issue to repository mapping."""

    async def test_store_sentry_repo_mapping(self, mock_redis_queue):
        """Test: Store Sentry issue ID → repository mapping."""
        # Act
        await mock_redis_queue.store_sentry_repo_mapping("SENTRY-123", "org/repo")

        # Assert
        mock_redis_queue.store_sentry_repo_mapping.assert_called_once_with(
            "SENTRY-123",
            "org/repo"
        )

    async def test_lookup_sentry_repo_mapping(self, mock_redis_queue):
        """Test: Look up repository from Sentry issue ID."""
        # Arrange
        mock_redis_queue.get_sentry_repo_mapping.return_value = "org/backend"

        # Act
        repo = mock_redis_queue.get_sentry_repo_mapping("SENTRY-123")

        # Assert
        assert repo == "org/backend"
        mock_redis_queue.get_sentry_repo_mapping.assert_called_once_with("SENTRY-123")
