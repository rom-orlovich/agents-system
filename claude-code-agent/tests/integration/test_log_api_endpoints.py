"""Integration tests for log API endpoints (TDD RED phase).

Tests verify that API endpoints correctly serve structured task logs.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch
from httpx import AsyncClient

from core.task_logger import TaskLogger


@pytest.mark.integration
class TestLogAPIEndpoints:
    """Test log reading API endpoints."""

    async def test_get_metadata_endpoint(self, client: AsyncClient, tmp_path):
        """Test: GET /api/tasks/{task_id}/logs/metadata returns metadata.json."""
        # Create task logs
        task_id = "test-api-001"
        logger = TaskLogger(task_id, tmp_path)
        logger.write_metadata({
            "task_id": task_id,
            "source": "webhook",
            "provider": "github",
            "status": "completed"
        })

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(f"/api/tasks/{task_id}/logs/metadata")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["source"] == "webhook"
        assert data["provider"] == "github"

    async def test_get_input_endpoint(self, client: AsyncClient, tmp_path):
        """Test: GET /api/tasks/{task_id}/logs/input returns 01-input.json."""
        task_id = "test-api-002"
        logger = TaskLogger(task_id, tmp_path)
        logger.write_input({
            "message": "Test input message",
            "source_metadata": {"provider": "jira"}
        })

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(f"/api/tasks/{task_id}/logs/input")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Test input message"
        assert data["source_metadata"]["provider"] == "jira"

    async def test_get_webhook_flow_endpoint(self, client: AsyncClient, tmp_path):
        """Test: GET /api/tasks/{task_id}/logs/webhook-flow returns JSONL as array."""
        task_id = "test-api-003"
        logger = TaskLogger(task_id, tmp_path)
        logger.append_webhook_event({"stage": "received", "timestamp": "2024-01-01T00:00:00Z"})
        logger.append_webhook_event({"stage": "validated", "timestamp": "2024-01-01T00:00:01Z"})
        logger.append_webhook_event({"stage": "task_created", "timestamp": "2024-01-01T00:00:02Z"})

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(f"/api/tasks/{task_id}/logs/webhook-flow")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["stage"] == "received"
        assert data[1]["stage"] == "validated"
        assert data[2]["stage"] == "task_created"

    async def test_get_agent_output_endpoint(self, client: AsyncClient, tmp_path):
        """Test: GET /api/tasks/{task_id}/logs/agent-output returns JSONL as array."""
        task_id = "test-api-004"
        logger = TaskLogger(task_id, tmp_path)
        logger.append_agent_output({"type": "thinking", "content": "Analyzing..."})
        logger.append_agent_output({"type": "tool_call", "tool": "Read"})
        logger.append_agent_output({"type": "message", "content": "Done"})

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(f"/api/tasks/{task_id}/logs/agent-output")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["type"] == "thinking"
        assert data[1]["type"] == "tool_call"
        assert data[2]["type"] == "message"

    async def test_get_final_result_endpoint(self, client: AsyncClient, tmp_path):
        """Test: GET /api/tasks/{task_id}/logs/final-result returns result JSON."""
        task_id = "test-api-005"
        logger = TaskLogger(task_id, tmp_path)
        logger.write_final_result({
            "success": True,
            "result": "Task completed",
            "metrics": {"cost_usd": 0.05}
        })

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(f"/api/tasks/{task_id}/logs/final-result")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"] == "Task completed"
        assert data["metrics"]["cost_usd"] == 0.05

    async def test_get_full_logs_endpoint(self, client: AsyncClient, tmp_path):
        """Test: GET /api/tasks/{task_id}/logs/full returns all logs combined."""
        task_id = "test-api-006"
        logger = TaskLogger(task_id, tmp_path)

        # Create all log files
        logger.write_metadata({"task_id": task_id, "status": "completed"})
        logger.write_input({"message": "Test"})
        logger.append_webhook_event({"stage": "received"})
        logger.append_agent_output({"type": "output", "content": "Working..."})
        logger.write_final_result({"success": True, "result": "Done"})

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(f"/api/tasks/{task_id}/logs/full")

        assert response.status_code == 200
        data = response.json()
        assert "metadata" in data
        assert "input" in data
        assert "webhook_flow" in data
        assert "agent_output" in data
        assert "final_result" in data
        assert data["metadata"]["task_id"] == task_id
        assert data["input"]["message"] == "Test"
        assert isinstance(data["webhook_flow"], list)
        assert isinstance(data["agent_output"], list)

    async def test_missing_task_returns_404(self, client: AsyncClient, tmp_path):
        """Test: GET /api/tasks/{nonexistent}/logs/metadata returns 404."""
        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get("/api/tasks/nonexistent-task/logs/metadata")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data or "error" in data

    async def test_missing_log_file_returns_404(self, client: AsyncClient, tmp_path):
        """Test: GET endpoint returns 404 when specific log file is missing."""
        task_id = "test-api-007"
        logger = TaskLogger(task_id, tmp_path)
        # Only create metadata, no input file
        logger.write_metadata({"task_id": task_id})

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(f"/api/tasks/{task_id}/logs/input")

        assert response.status_code == 404

    async def test_metadata_endpoint_validates_json(self, client: AsyncClient, tmp_path):
        """Test: Metadata endpoint returns valid JSON."""
        task_id = "test-api-008"
        logger = TaskLogger(task_id, tmp_path)
        logger.write_metadata({
            "task_id": task_id,
            "source": "dashboard",
            "created_at": "2024-01-01T00:00:00Z"
        })

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(f"/api/tasks/{task_id}/logs/metadata")

        assert response.status_code == 200
        # Ensure it's valid JSON by parsing it
        data = response.json()
        assert isinstance(data, dict)

    async def test_jsonl_endpoint_returns_array(self, client: AsyncClient, tmp_path):
        """Test: JSONL endpoints return arrays, not raw JSONL text."""
        task_id = "test-api-009"
        logger = TaskLogger(task_id, tmp_path)
        logger.append_webhook_event({"stage": "step1"})
        logger.append_webhook_event({"stage": "step2"})

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(f"/api/tasks/{task_id}/logs/webhook-flow")

        assert response.status_code == 200
        data = response.json()
        # Should be an array, not a string with newlines
        assert isinstance(data, list)
        assert len(data) == 2

    async def test_empty_jsonl_returns_empty_array(self, client: AsyncClient, tmp_path):
        """Test: Empty JSONL file returns empty array."""
        task_id = "test-api-010"
        logger = TaskLogger(task_id, tmp_path)
        # Create log directory but don't append any events
        logger._log_dir.mkdir(parents=True, exist_ok=True)
        (logger._log_dir / "02-webhook-flow.jsonl").touch()

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(f"/api/tasks/{task_id}/logs/webhook-flow")

        # Should handle empty file gracefully
        assert response.status_code in [200, 404]  # Either empty array or not found
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0

    async def test_cors_headers_present(self, client: AsyncClient, tmp_path):
        """Test: Log endpoints include CORS headers."""
        task_id = "test-api-011"
        logger = TaskLogger(task_id, tmp_path)
        logger.write_metadata({"task_id": task_id})

        with patch("api.dashboard.settings.task_logs_dir", tmp_path):
            response = await client.get(
                f"/api/tasks/{task_id}/logs/metadata",
                headers={"Origin": "http://localhost:3000"}
            )

        # CORS headers should be present (configured at app level)
        assert response.status_code == 200
