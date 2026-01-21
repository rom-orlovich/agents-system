"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health endpoint returns status."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "machine_id" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_endpoint(client: AsyncClient):
    """Status endpoint returns machine status."""
    response = await client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "machine_id" in data
    assert "status" in data
    assert "queue_length" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tasks_endpoint(client: AsyncClient):
    """List tasks endpoint returns task list."""
    response = await client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_agents_endpoint(client: AsyncClient):
    """List agents endpoint returns agents."""
    response = await client.get("/api/agents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should have at least planning and executor
    assert len(data) >= 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_webhooks_endpoint(client: AsyncClient):
    """List webhooks endpoint returns webhooks."""
    response = await client.get("/api/webhooks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_nonexistent_task(client: AsyncClient):
    """Getting nonexistent task returns 404."""
    response = await client.get("/api/tasks/nonexistent")
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_github_webhook_endpoint(client: AsyncClient):
    """GitHub webhook endpoint accepts POST."""
    payload = {
        "action": "opened",
        "issue": {
            "number": 123,
            "title": "Test issue",
            "body": "Test body"
        }
    }
    headers = {"X-GitHub-Event": "issues"}

    response = await client.post(
        "/webhooks/github",
        json=payload,
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
