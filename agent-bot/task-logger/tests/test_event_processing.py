"""Tests for task logger event processing business logic.

Tests the core event processing logic and routing.
"""

import json
from pathlib import Path
from datetime import datetime, timezone


class MockTaskLogger:
    """Mock TaskLogger for testing event processing."""

    def __init__(self, task_id: str, logs_dir: Path):
        self.task_id = task_id
        self.logs_dir = logs_dir
        self.metadata_written = None
        self.input_written = None
        self.webhook_events = []
        self.agent_outputs = []
        self.user_inputs = []
        self.knowledge_interactions = []
        self.final_result = None

    def write_metadata(self, metadata: dict) -> None:
        self.metadata_written = metadata

    def write_input(self, input_data: dict) -> None:
        self.input_written = input_data

    def append_webhook_event(self, event: dict) -> None:
        self.webhook_events.append(event)

    def append_agent_output(self, output: dict) -> None:
        self.agent_outputs.append(output)

    def append_user_input(self, user_input: dict) -> None:
        self.user_inputs.append(user_input)

    def append_knowledge_interaction(self, interaction: dict) -> None:
        self.knowledge_interactions.append(interaction)

    def write_final_result(self, result: dict) -> None:
        self.final_result = result


webhook_buffer: dict[str, list[dict]] = {}
loggers_cache: dict[str, MockTaskLogger] = {}


def get_or_create_mock_logger(
    task_id: str, logs_dir: Path = Path("/tmp")
) -> MockTaskLogger:
    """Get or create a mock logger for testing."""
    if task_id not in loggers_cache:
        loggers_cache[task_id] = MockTaskLogger(task_id, logs_dir)
    return loggers_cache[task_id]


def reset_test_state():
    """Reset test state between tests."""
    global webhook_buffer, loggers_cache
    webhook_buffer = {}
    loggers_cache = {}


async def process_webhook_event_mock(event: dict):
    """Mock webhook event processor."""
    webhook_event_id = event.get("webhook_event_id")
    event_type = event.get("type")
    data = event.get("data", {})
    timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())

    if isinstance(data, str):
        data = json.loads(data)

    task_id = data.get("task_id")

    if not task_id:
        if webhook_event_id not in webhook_buffer:
            webhook_buffer[webhook_event_id] = []
        webhook_buffer[webhook_event_id].append(
            {
                "timestamp": timestamp,
                "stage": event_type.split(":")[1],
                "data": data,
            }
        )
        return

    task_logger = get_or_create_mock_logger(task_id)

    for buffered in webhook_buffer.pop(webhook_event_id, []):
        task_logger.append_webhook_event(buffered)

    task_logger.append_webhook_event(
        {
            "timestamp": timestamp,
            "stage": event_type.split(":")[1],
            "data": data,
        }
    )


async def process_task_event_mock(event: dict):
    """Mock task event processor."""
    task_id = event.get("task_id")
    if not task_id:
        return

    event_type = event.get("type")
    data = event.get("data", {})
    timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())

    if isinstance(data, str):
        data = json.loads(data)

    task_logger = get_or_create_mock_logger(task_id)

    if event_type == "task:created":
        task_logger.write_metadata(data)
        task_logger.write_input({"message": data.get("input_message")})

    elif event_type == "task:output":
        task_logger.append_agent_output(
            {
                "timestamp": timestamp,
                "type": "output",
                "content": data.get("content"),
            }
        )

    elif event_type == "task:user_input":
        task_logger.append_user_input(
            {
                "timestamp": timestamp,
                "type": "user_response",
                "question_type": data.get("question_type", "clarification"),
                "content": data.get("content"),
            }
        )

    elif event_type == "task:completed":
        task_logger.write_final_result(
            {
                "success": True,
                "result": data.get("result"),
                "metrics": {
                    "cost_usd": data.get("cost_usd"),
                    "duration_seconds": data.get("duration_seconds"),
                },
                "completed_at": timestamp,
            }
        )

    elif event_type == "task:failed":
        task_logger.write_final_result(
            {
                "success": False,
                "error": data.get("error"),
                "completed_at": timestamp,
            }
        )


class TestWebhookEventBuffering:
    """Tests for webhook event buffering."""

    def setup_method(self):
        """Reset state before each test."""
        reset_test_state()

    async def test_webhook_events_buffered_until_task_id_known(self):
        """Business requirement: Early events buffered."""
        webhook_event_id = "webhook-001"

        await process_webhook_event_mock(
            {
                "type": "webhook:received",
                "webhook_event_id": webhook_event_id,
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {"provider": "github"},
            }
        )

        await process_webhook_event_mock(
            {
                "type": "webhook:validated",
                "webhook_event_id": webhook_event_id,
                "timestamp": "2026-01-31T12:00:01Z",
                "data": {"valid": True},
            }
        )

        assert webhook_event_id in webhook_buffer
        assert len(webhook_buffer[webhook_event_id]) == 2

    async def test_webhook_events_written_in_order(self):
        """Business requirement: Event ordering preserved."""
        webhook_event_id = "webhook-001"
        task_id = "task-001"

        await process_webhook_event_mock(
            {
                "type": "webhook:received",
                "webhook_event_id": webhook_event_id,
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {},
            }
        )

        await process_webhook_event_mock(
            {
                "type": "webhook:validated",
                "webhook_event_id": webhook_event_id,
                "timestamp": "2026-01-31T12:00:01Z",
                "data": {},
            }
        )

        await process_webhook_event_mock(
            {
                "type": "webhook:task_created",
                "webhook_event_id": webhook_event_id,
                "timestamp": "2026-01-31T12:00:02Z",
                "data": {"task_id": task_id},
            }
        )

        task_logger = loggers_cache[task_id]
        assert len(task_logger.webhook_events) == 3
        assert task_logger.webhook_events[0]["stage"] == "received"
        assert task_logger.webhook_events[1]["stage"] == "validated"
        assert task_logger.webhook_events[2]["stage"] == "task_created"


class TestTaskEventProcessing:
    """Tests for task event processing."""

    def setup_method(self):
        """Reset state before each test."""
        reset_test_state()

    async def test_task_created_writes_metadata(self):
        """Business requirement: Metadata captured."""
        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": "task-001",
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {
                    "task_id": "task-001",
                    "source": "webhook",
                    "assigned_agent": "github-issue-handler",
                    "input_message": "Fix the bug",
                },
            }
        )

        task_logger = loggers_cache["task-001"]
        assert task_logger.metadata_written is not None
        assert task_logger.metadata_written["source"] == "webhook"

    async def test_task_created_writes_input(self):
        """Business requirement: Initial input preserved."""
        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": "task-001",
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {"input_message": "Fix the authentication bug"},
            }
        )

        task_logger = loggers_cache["task-001"]
        assert task_logger.input_written is not None
        assert task_logger.input_written["message"] == "Fix the authentication bug"

    async def test_task_output_appends_to_stream(self):
        """Business requirement: Streaming output captured."""
        task_id = "task-001"

        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": task_id,
                "data": {"input_message": "test"},
            }
        )

        await process_task_event_mock(
            {
                "type": "task:output",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {"content": "Analyzing the code..."},
            }
        )

        await process_task_event_mock(
            {
                "type": "task:output",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:01Z",
                "data": {"content": "Found the bug!"},
            }
        )

        task_logger = loggers_cache[task_id]
        assert len(task_logger.agent_outputs) == 2

    async def test_user_input_captured_separately(self):
        """Business requirement: User responses tracked."""
        task_id = "task-001"

        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": task_id,
                "data": {"input_message": "test"},
            }
        )

        await process_task_event_mock(
            {
                "type": "task:user_input",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {
                    "question_type": "approval",
                    "content": "yes, proceed",
                },
            }
        )

        task_logger = loggers_cache[task_id]
        assert len(task_logger.user_inputs) == 1
        assert task_logger.user_inputs[0]["question_type"] == "approval"

    async def test_task_completed_writes_final_result(self):
        """Business requirement: Success metrics captured."""
        task_id = "task-001"

        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": task_id,
                "data": {"input_message": "test"},
            }
        )

        await process_task_event_mock(
            {
                "type": "task:completed",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:02:00Z",
                "data": {
                    "result": "Bug fixed successfully",
                    "cost_usd": 0.05,
                    "duration_seconds": 120,
                },
            }
        )

        task_logger = loggers_cache[task_id]
        assert task_logger.final_result is not None
        assert task_logger.final_result["success"] is True
        assert task_logger.final_result["metrics"]["cost_usd"] == 0.05

    async def test_task_failed_writes_error_details(self):
        """Business requirement: Failure debugging."""
        task_id = "task-001"

        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": task_id,
                "data": {"input_message": "test"},
            }
        )

        await process_task_event_mock(
            {
                "type": "task:failed",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:02:00Z",
                "data": {"error": "Timeout exceeded"},
            }
        )

        task_logger = loggers_cache[task_id]
        assert task_logger.final_result is not None
        assert task_logger.final_result["success"] is False
        assert task_logger.final_result["error"] == "Timeout exceeded"


class TestEventResilience:
    """Tests for event processing resilience."""

    def setup_method(self):
        """Reset state before each test."""
        reset_test_state()

    async def test_missing_task_id_handled(self):
        """Business requirement: Resilience for missing task_id."""
        await process_task_event_mock(
            {
                "type": "task:output",
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {"content": "test"},
            }
        )

        assert len(loggers_cache) == 0

    async def test_json_string_data_parsed(self):
        """JSON string data is properly parsed."""
        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": "task-001",
                "timestamp": "2026-01-31T12:00:00Z",
                "data": json.dumps({"input_message": "Fix bug"}),
            }
        )

        task_logger = loggers_cache["task-001"]
        assert task_logger.input_written["message"] == "Fix bug"


async def process_knowledge_event_mock(event: dict):
    """Mock knowledge event processor."""
    task_id = event.get("task_id")
    if not task_id:
        return

    event_type = event.get("type")
    data = event.get("data", {})
    timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())

    if isinstance(data, str):
        data = json.loads(data)

    task_logger = get_or_create_mock_logger(task_id)

    if event_type == "knowledge:query":
        task_logger.append_knowledge_interaction(
            {
                "timestamp": timestamp,
                "type": "query",
                "tool_name": data.get("tool_name", "unknown"),
                "query": data.get("query", ""),
                "source_types": data.get("source_types", []),
                "org_id": data.get("org_id"),
            }
        )

    elif event_type == "knowledge:result":
        task_logger.append_knowledge_interaction(
            {
                "timestamp": timestamp,
                "type": "result",
                "tool_name": data.get("tool_name", "unknown"),
                "query": data.get("query", ""),
                "results_count": data.get("results_count", 0),
                "results_preview": data.get("results_preview", [])[:5],
                "query_time_ms": data.get("query_time_ms", 0.0),
                "cached": data.get("cached", False),
            }
        )

    elif event_type == "knowledge:tool_call":
        task_logger.append_knowledge_interaction(
            {
                "timestamp": timestamp,
                "type": "tool_call",
                "tool_name": data.get("tool_name", "unknown"),
                "parameters": data.get("parameters", {}),
            }
        )

    elif event_type == "knowledge:context_used":
        task_logger.append_knowledge_interaction(
            {
                "timestamp": timestamp,
                "type": "context_used",
                "tool_name": data.get("tool_name", "unknown"),
                "contexts_count": data.get("contexts_count", 0),
                "relevance_scores": data.get("relevance_scores", []),
                "total_tokens": data.get("total_tokens"),
            }
        )


class TestKnowledgeEventProcessing:
    """Tests for knowledge event processing business logic."""

    def setup_method(self):
        """Reset state before each test."""
        reset_test_state()

    async def test_knowledge_query_event_logged(self):
        """Knowledge query events are captured with all fields."""
        task_id = "task-001"

        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": task_id,
                "data": {"input_message": "test"},
            }
        )

        await process_knowledge_event_mock(
            {
                "type": "knowledge:query",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {
                    "tool_name": "knowledge_query",
                    "query": "authentication error handling",
                    "source_types": ["code", "jira"],
                    "org_id": "org-123",
                },
            }
        )

        task_logger = loggers_cache[task_id]
        assert len(task_logger.knowledge_interactions) == 1

        interaction = task_logger.knowledge_interactions[0]
        assert interaction["type"] == "query"
        assert interaction["tool_name"] == "knowledge_query"
        assert interaction["query"] == "authentication error handling"
        assert interaction["source_types"] == ["code", "jira"]
        assert interaction["org_id"] == "org-123"

    async def test_knowledge_result_event_logged(self):
        """Knowledge result events capture search results."""
        task_id = "task-001"

        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": task_id,
                "data": {"input_message": "test"},
            }
        )

        await process_knowledge_event_mock(
            {
                "type": "knowledge:result",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:01Z",
                "data": {
                    "tool_name": "knowledge_query",
                    "query": "authentication error handling",
                    "results_count": 5,
                    "results_preview": [
                        {
                            "source_type": "code",
                            "source_id": "auth/handler.py",
                            "relevance_score": 0.92,
                        }
                    ],
                    "query_time_ms": 245.7,
                    "cached": False,
                },
            }
        )

        task_logger = loggers_cache[task_id]
        assert len(task_logger.knowledge_interactions) == 1

        interaction = task_logger.knowledge_interactions[0]
        assert interaction["type"] == "result"
        assert interaction["results_count"] == 5
        assert interaction["query_time_ms"] == 245.7
        assert interaction["cached"] is False
        assert len(interaction["results_preview"]) == 1
        assert interaction["results_preview"][0]["relevance_score"] == 0.92

    async def test_knowledge_query_result_pair_captured(self):
        """Query and result events form a complete interaction."""
        task_id = "task-001"

        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": task_id,
                "data": {"input_message": "test"},
            }
        )

        await process_knowledge_event_mock(
            {
                "type": "knowledge:query",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {
                    "tool_name": "code_search",
                    "query": "validate_token",
                    "source_types": ["code"],
                    "org_id": "org-123",
                },
            }
        )

        await process_knowledge_event_mock(
            {
                "type": "knowledge:result",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:01Z",
                "data": {
                    "tool_name": "code_search",
                    "query": "validate_token",
                    "results_count": 3,
                    "results_preview": [],
                    "query_time_ms": 150.0,
                    "cached": True,
                },
            }
        )

        task_logger = loggers_cache[task_id]
        assert len(task_logger.knowledge_interactions) == 2

        query = task_logger.knowledge_interactions[0]
        result = task_logger.knowledge_interactions[1]

        assert query["type"] == "query"
        assert result["type"] == "result"
        assert query["tool_name"] == result["tool_name"]
        assert query["query"] == result["query"]

    async def test_knowledge_context_used_event_logged(self):
        """Context usage events track how results were used."""
        task_id = "task-001"

        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": task_id,
                "data": {"input_message": "test"},
            }
        )

        await process_knowledge_event_mock(
            {
                "type": "knowledge:context_used",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:02Z",
                "data": {
                    "tool_name": "knowledge_query",
                    "contexts_count": 3,
                    "relevance_scores": [0.92, 0.87, 0.81],
                    "total_tokens": 2450,
                },
            }
        )

        task_logger = loggers_cache[task_id]
        assert len(task_logger.knowledge_interactions) == 1

        interaction = task_logger.knowledge_interactions[0]
        assert interaction["type"] == "context_used"
        assert interaction["contexts_count"] == 3
        assert interaction["relevance_scores"] == [0.92, 0.87, 0.81]
        assert interaction["total_tokens"] == 2450

    async def test_knowledge_event_without_task_id_ignored(self):
        """Knowledge events without task_id are gracefully ignored."""
        await process_knowledge_event_mock(
            {
                "type": "knowledge:query",
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {
                    "tool_name": "knowledge_query",
                    "query": "test",
                },
            }
        )

        assert len(loggers_cache) == 0

    async def test_results_preview_limited_to_five(self):
        """Results preview is limited to 5 items."""
        task_id = "task-001"

        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": task_id,
                "data": {"input_message": "test"},
            }
        )

        many_results = [
            {"source_id": f"file-{i}.py", "relevance_score": 0.9 - i * 0.05}
            for i in range(10)
        ]

        await process_knowledge_event_mock(
            {
                "type": "knowledge:result",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:01Z",
                "data": {
                    "tool_name": "code_search",
                    "query": "test",
                    "results_count": 10,
                    "results_preview": many_results,
                    "query_time_ms": 100.0,
                },
            }
        )

        task_logger = loggers_cache[task_id]
        interaction = task_logger.knowledge_interactions[0]
        assert len(interaction["results_preview"]) == 5

    async def test_multiple_knowledge_tools_tracked_separately(self):
        """Different knowledge tools are tracked in sequence."""
        task_id = "task-001"

        await process_task_event_mock(
            {
                "type": "task:created",
                "task_id": task_id,
                "data": {"input_message": "test"},
            }
        )

        await process_knowledge_event_mock(
            {
                "type": "knowledge:query",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:00Z",
                "data": {
                    "tool_name": "knowledge_query",
                    "query": "auth",
                    "source_types": ["code", "jira"],
                    "org_id": "org-1",
                },
            }
        )

        await process_knowledge_event_mock(
            {
                "type": "knowledge:query",
                "task_id": task_id,
                "timestamp": "2026-01-31T12:00:02Z",
                "data": {
                    "tool_name": "code_search",
                    "query": "validate_token",
                    "source_types": ["code"],
                    "org_id": "org-1",
                },
            }
        )

        task_logger = loggers_cache[task_id]
        assert len(task_logger.knowledge_interactions) == 2

        tools_used = [i["tool_name"] for i in task_logger.knowledge_interactions]
        assert "knowledge_query" in tools_used
        assert "code_search" in tools_used
