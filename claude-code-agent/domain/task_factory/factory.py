"""
Unified task factory implementation.

This factory consolidates the task creation logic from:
- github/utils.py: create_github_task (93 lines)
- jira/utils.py: create_jira_task (106 lines)
- slack/utils.py: create_slack_task (93 lines)

Common code (should be in factory):
- Session creation (identical)
- Task DB creation (identical structure)
- External ID generation (identical)
- Flow ID generation (identical)
- Conversation creation (identical)
- Claude tasks sync (identical)
- Redis task push (identical)
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

import structlog

from domain.exceptions import WebhookValidationError
from shared.machine_models import TaskStatus, AgentType, WebhookCommand

logger = structlog.get_logger()


class DatabaseSessionProtocol(Protocol):
    """Protocol for database session."""

    def add(self, instance: Any) -> None:
        """Add an instance to the session."""
        ...

    async def flush(self) -> None:
        """Flush pending changes."""
        ...

    async def commit(self) -> None:
        """Commit the transaction."""
        ...


class RedisClientProtocol(Protocol):
    """Protocol for Redis client."""

    async def push_task(self, task_id: str) -> None:
        """Push task to queue."""
        ...


class WebhookTaskFactory:
    """
    Unified factory for creating webhook tasks.

    Provides consistent task creation for all webhook sources
    (GitHub, Jira, Slack) with proper metadata, session,
    and conversation handling.
    """

    def __init__(
        self,
        db: DatabaseSessionProtocol,
        redis_client: RedisClientProtocol,
    ):
        """
        Initialize task factory.

        Args:
            db: Database session for persistence
            redis_client: Redis client for task queue
        """
        self.db = db
        self.redis = redis_client

    def generate_task_id(self) -> str:
        """Generate unique task ID."""
        return f"task-{uuid.uuid4().hex[:12]}"

    def generate_session_id(self) -> str:
        """Generate unique session ID for webhook tasks."""
        return f"webhook-{uuid.uuid4().hex[:12]}"

    def generate_external_id(self, source: str, payload: Dict[str, Any]) -> str:
        """
        Generate external ID for task deduplication.

        Args:
            source: Webhook source (github, jira, slack)
            payload: Webhook payload

        Returns:
            External ID string
        """
        if source == "github":
            repo = payload.get("repository", {}).get("full_name", "unknown")
            issue = payload.get("issue") or payload.get("pull_request") or {}
            number = issue.get("number", "0")
            return f"github:{repo}:{number}"

        elif source == "jira":
            issue_key = payload.get("issue", {}).get("key", "unknown")
            return f"jira:{issue_key}"

        elif source == "slack":
            event = payload.get("event", {})
            channel = event.get("channel", "unknown")
            ts = event.get("ts", "0")
            return f"slack:{channel}:{ts}"

        return f"{source}:{uuid.uuid4().hex[:8]}"

    def generate_flow_id(self, external_id: str) -> str:
        """
        Generate deterministic flow ID from external ID.

        The flow ID is used to group related tasks in the same
        conversation flow (e.g., multiple commands on same PR).

        Args:
            external_id: External ID for the task

        Returns:
            Flow ID (deterministic hash-based)
        """
        hash_obj = hashlib.md5(external_id.encode())
        hash_hex = hash_obj.hexdigest()[:12]
        return f"flow-{hash_hex}"

    async def create_task(
        self,
        source: str,
        command: WebhookCommand,
        payload: Dict[str, Any],
        completion_handler: str,
        routing_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a task from webhook.

        This is the unified task creation method that replaces
        create_github_task, create_jira_task, and create_slack_task.

        Args:
            source: Webhook source (github, jira, slack)
            command: Matched webhook command
            payload: Webhook payload
            completion_handler: Module path for completion handler
            routing_metadata: Optional routing metadata override

        Returns:
            Created task ID
        """
        # Validate inputs
        validate_task_creation(command, payload)

        # Generate IDs
        task_id = self.generate_task_id()
        session_id = self.generate_session_id()
        external_id = self.generate_external_id(source, payload)
        flow_id = self.generate_flow_id(external_id)

        # Extract metadata
        if routing_metadata is None:
            routing_metadata = extract_metadata(source, payload)

        # Render prompt
        message = self._render_prompt(command, payload, task_id)

        # Create session
        await self._create_session(session_id)

        # Create task
        task_db = await self._create_task_db(
            task_id=task_id,
            session_id=session_id,
            message=message,
            source=source,
            command=command,
            payload=payload,
            completion_handler=completion_handler,
            routing_metadata=routing_metadata,
            flow_id=flow_id,
            external_id=external_id,
        )

        # Create conversation
        conversation_id = await self._create_conversation(task_db, flow_id)
        if conversation_id:
            logger.info(
                "task_factory_conversation_created",
                conversation_id=conversation_id,
                task_id=task_id,
            )

        # Sync to Claude tasks (optional)
        await self._sync_to_claude_tasks(task_db, flow_id, conversation_id)

        # Commit changes
        await self.db.commit()

        # Push to queue
        await self.redis.push_task(task_id)

        logger.info(
            "task_factory_task_created",
            task_id=task_id,
            source=source,
            command=command.name,
        )

        return task_id

    def _render_prompt(
        self,
        command: WebhookCommand,
        payload: Dict[str, Any],
        task_id: str,
    ) -> str:
        """Render prompt template with payload data."""
        try:
            from core.webhook_engine import render_template, wrap_prompt_with_brain_instructions

            base_message = render_template(command.prompt_template, payload, task_id=task_id)
            return wrap_prompt_with_brain_instructions(base_message, task_id=task_id)
        except Exception as e:
            logger.warning(
                "task_factory_prompt_render_failed",
                error=str(e),
                task_id=task_id,
            )
            # Fallback to raw template
            return command.prompt_template

    async def _create_session(self, session_id: str) -> None:
        """Create webhook session."""
        from core.database.models import SessionDB

        session_db = SessionDB(
            session_id=session_id,
            user_id="webhook-system",
            machine_id="claude-agent-001",
            connected_at=datetime.now(timezone.utc),
        )
        self.db.add(session_db)

    async def _create_task_db(
        self,
        task_id: str,
        session_id: str,
        message: str,
        source: str,
        command: WebhookCommand,
        payload: Dict[str, Any],
        completion_handler: str,
        routing_metadata: Dict[str, Any],
        flow_id: str,
        external_id: str,
    ):
        """Create task database record."""
        from core.database.models import TaskDB

        # Map agent type
        agent_type_map = {
            "planning": AgentType.PLANNING,
            "executor": AgentType.EXECUTOR,
            "brain": AgentType.PLANNING,
        }
        agent_type = agent_type_map.get("brain", AgentType.PLANNING)

        # Build source metadata
        source_metadata = {
            "webhook_source": source,
            "webhook_name": f"{source}-webhook",
            "command": command.name,
            "original_target_agent": command.target_agent,
            "routing": routing_metadata,
            "payload": payload,
            "completion_handler": completion_handler,
            "flow_id": flow_id,
            "external_id": external_id,
        }

        task_db = TaskDB(
            task_id=task_id,
            session_id=session_id,
            user_id="webhook-system",
            assigned_agent="brain",
            agent_type=agent_type,
            status=TaskStatus.QUEUED,
            input_message=message,
            source="webhook",
            source_metadata=json.dumps(source_metadata),
            flow_id=flow_id,
        )
        self.db.add(task_db)
        await self.db.flush()

        return task_db

    async def _create_conversation(self, task_db, flow_id: str) -> Optional[str]:
        """Create or get conversation for task."""
        try:
            from core.webhook_engine import create_webhook_conversation

            return await create_webhook_conversation(task_db, self.db)
        except Exception as e:
            logger.warning(
                "task_factory_conversation_failed",
                task_id=task_db.task_id,
                error=str(e),
            )
            return None

    async def _sync_to_claude_tasks(
        self,
        task_db,
        flow_id: str,
        conversation_id: Optional[str],
    ) -> None:
        """Sync task to Claude tasks (optional feature)."""
        try:
            from core.claude_tasks_sync import sync_task_to_claude_tasks

            claude_task_id = sync_task_to_claude_tasks(
                task_db=task_db,
                flow_id=flow_id,
                conversation_id=conversation_id,
            )
            if claude_task_id:
                # Update source metadata with Claude task ID
                source_metadata = json.loads(task_db.source_metadata or "{}")
                source_metadata["claude_task_id"] = claude_task_id
                task_db.source_metadata = json.dumps(source_metadata)
        except Exception as e:
            logger.warning(
                "task_factory_claude_sync_failed",
                task_id=task_db.task_id,
                error=str(e),
            )


def extract_metadata(source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract routing metadata from payload.

    Args:
        source: Webhook source
        payload: Webhook payload

    Returns:
        Routing metadata dictionary
    """
    if source == "github":
        repo = payload.get("repository", {}).get("full_name", "")
        pr = payload.get("pull_request") or {}
        issue = payload.get("issue") or {}
        pr_number = pr.get("number") or issue.get("number")

        return {
            "repo": repo,
            "pr_number": pr_number,
            "source": "github",
        }

    elif source == "jira":
        issue_key = payload.get("issue", {}).get("key", "")

        return {
            "ticket_key": issue_key,
            "source": "jira",
        }

    elif source == "slack":
        event = payload.get("event", {})

        return {
            "channel": event.get("channel"),
            "thread_ts": event.get("ts"),
            "source": "slack",
        }

    return {"source": source}


def validate_task_creation(
    command: Optional[WebhookCommand],
    payload: Optional[Dict[str, Any]],
) -> None:
    """
    Validate task creation inputs.

    Args:
        command: Webhook command
        payload: Webhook payload

    Raises:
        WebhookValidationError: If validation fails
    """
    if command is None:
        raise WebhookValidationError(
            "Command is required for task creation",
            field="command",
        )

    if payload is None:
        raise WebhookValidationError(
            "Payload is required for task creation",
            field="payload",
        )
