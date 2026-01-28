"""
Tests for unified task factory - written first following TDD approach.

The task factory consolidates create_github_task, create_jira_task,
create_slack_task into a single unified implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTaskFactory:
    """Tests for WebhookTaskFactory."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis = AsyncMock()
        redis.push_task = AsyncMock()
        return redis

    @pytest.fixture
    def factory(self, mock_db, mock_redis):
        """Create task factory with mocks."""
        from domain.task_factory import WebhookTaskFactory

        return WebhookTaskFactory(
            db=mock_db,
            redis_client=mock_redis,
        )

    def test_generate_task_id(self, factory):
        """Test task ID generation."""
        task_id = factory.generate_task_id()

        assert task_id.startswith("task-")
        assert len(task_id) == 17  # "task-" + 12 hex chars

    def test_generate_task_id_unique(self, factory):
        """Test task IDs are unique."""
        ids = [factory.generate_task_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_generate_session_id(self, factory):
        """Test session ID generation."""
        session_id = factory.generate_session_id()

        assert session_id.startswith("webhook-")
        assert len(session_id) == 20  # "webhook-" + 12 hex chars

    def test_generate_external_id_github(self, factory):
        """Test external ID generation for GitHub."""
        payload = {
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123},
        }

        external_id = factory.generate_external_id("github", payload)

        assert "github" in external_id
        assert "owner/repo" in external_id
        assert "123" in external_id

    def test_generate_external_id_jira(self, factory):
        """Test external ID generation for Jira."""
        payload = {
            "issue": {"key": "PROJ-456"},
        }

        external_id = factory.generate_external_id("jira", payload)

        assert "jira" in external_id
        assert "PROJ-456" in external_id

    def test_generate_external_id_slack(self, factory):
        """Test external ID generation for Slack."""
        payload = {
            "event": {
                "channel": "C12345",
                "ts": "123.456",
            },
        }

        external_id = factory.generate_external_id("slack", payload)

        assert "slack" in external_id
        assert "C12345" in external_id

    def test_generate_flow_id(self, factory):
        """Test flow ID generation."""
        external_id = "github:owner/repo:123"

        flow_id = factory.generate_flow_id(external_id)

        # Should be deterministic
        flow_id2 = factory.generate_flow_id(external_id)
        assert flow_id == flow_id2

        # Should have proper format
        assert flow_id.startswith("flow-")

    @pytest.mark.asyncio
    async def test_create_task_basic(self, factory, mock_db, mock_redis):
        """Test basic task creation."""
        from shared.machine_models import WebhookCommand

        command = WebhookCommand(
            name="review",
            target_agent="brain",
            prompt_template="Review this: {content}",
        )
        payload = {
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123, "body": "Fix this bug"},
        }
        completion_handler = "api.webhooks.github.routes.handle_github_task_completion"

        task_id = await factory.create_task(
            source="github",
            command=command,
            payload=payload,
            completion_handler=completion_handler,
        )

        assert task_id.startswith("task-")
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
        mock_redis.push_task.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_create_task_creates_session(self, factory, mock_db, mock_redis):
        """Test that task creation creates a session."""
        from shared.machine_models import WebhookCommand

        command = WebhookCommand(
            name="review",
            target_agent="brain",
            prompt_template="Review this",
        )
        payload = {"repository": {"full_name": "owner/repo"}}

        await factory.create_task(
            source="github",
            command=command,
            payload=payload,
            completion_handler="handler",
        )

        # Should have added both session and task
        assert mock_db.add.call_count >= 2

    @pytest.mark.asyncio
    async def test_create_task_stores_metadata(self, factory, mock_db, mock_redis):
        """Test that task stores proper metadata."""
        from shared.machine_models import WebhookCommand

        command = WebhookCommand(
            name="review",
            target_agent="brain",
            prompt_template="Review this",
        )
        payload = {
            "repository": {"full_name": "owner/repo"},
            "routing": {"pr_number": 123},
        }
        completion_handler = "api.webhooks.github.routes.handle_github_task_completion"

        await factory.create_task(
            source="github",
            command=command,
            payload=payload,
            completion_handler=completion_handler,
        )

        # Verify task was created with proper metadata
        calls = mock_db.add.call_args_list
        task_call = next((c for c in calls if hasattr(c[0][0], 'task_id')), None)
        assert task_call is not None


class TestMetadataExtractor:
    """Tests for metadata extraction."""

    def test_extract_github_metadata(self):
        """Test extracting GitHub metadata."""
        from domain.task_factory import extract_metadata

        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123},
        }

        metadata = extract_metadata("github", payload)

        assert metadata.get("repo") == "owner/repo"
        assert metadata.get("pr_number") == 123

    def test_extract_jira_metadata(self):
        """Test extracting Jira metadata."""
        from domain.task_factory import extract_metadata

        payload = {
            "issue": {"key": "PROJ-456"},
        }

        metadata = extract_metadata("jira", payload)

        assert metadata.get("ticket_key") == "PROJ-456"

    def test_extract_slack_metadata(self):
        """Test extracting Slack metadata."""
        from domain.task_factory import extract_metadata

        payload = {
            "event": {
                "channel": "C12345",
                "ts": "123.456",
            },
        }

        metadata = extract_metadata("slack", payload)

        assert metadata.get("channel") == "C12345"


class TestTaskValidation:
    """Tests for task validation."""

    def test_validate_command(self):
        """Test command validation."""
        from domain.task_factory import validate_task_creation
        from shared.machine_models import WebhookCommand

        command = WebhookCommand(
            name="review",
            target_agent="brain",
            prompt_template="Review this",
        )
        payload = {"repository": {"name": "test"}}

        # Should not raise
        validate_task_creation(command, payload)

    def test_validate_missing_payload(self):
        """Test validation with missing payload."""
        from domain.task_factory import validate_task_creation
        from shared.machine_models import WebhookCommand
        from domain.exceptions import WebhookValidationError

        command = WebhookCommand(
            name="review",
            target_agent="brain",
            prompt_template="Review this",
        )

        with pytest.raises(WebhookValidationError):
            validate_task_creation(command, None)

    def test_validate_missing_command(self):
        """Test validation with missing command."""
        from domain.task_factory import validate_task_creation
        from domain.exceptions import WebhookValidationError

        payload = {"repository": {"name": "test"}}

        with pytest.raises(WebhookValidationError):
            validate_task_creation(None, payload)
