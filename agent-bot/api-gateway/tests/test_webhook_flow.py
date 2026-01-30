import pytest
from httpx import AsyncClient
from main import app
import json
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_logs_dir():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api-gateway"
    assert "queue_length" in data


@pytest.mark.asyncio
async def test_github_webhook_complete_flow(client: AsyncClient, temp_logs_dir: Path):
    payload = {
        "action": "created",
        "issue": {"number": 42, "body": "@agent analyze this issue"},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "test-user"},
    }

    response = await client.post(
        "/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "issues"},
    )

    assert response.status_code == 200

    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["task_id"] is not None
    assert response_data["error"] is None


@pytest.mark.asyncio
async def test_github_webhook_invalid_payload(client: AsyncClient):
    payload = {"invalid": "payload"}

    response = await client.post(
        "/webhooks/github",
        json=payload,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_jira_webhook_complete_flow(client: AsyncClient):
    payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "PROJ-123",
            "fields": {"description": "Test description"},
        },
        "user": {"accountId": "user-123"},
    }

    response = await client.post(
        "/webhooks/jira",
        json=payload,
    )

    assert response.status_code == 200

    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["task_id"] is not None


@pytest.mark.asyncio
async def test_slack_webhook_complete_flow(client: AsyncClient):
    payload = {
        "type": "event_callback",
        "event": {"type": "message", "text": "Hello agent", "user": "U123"},
    }

    response = await client.post(
        "/webhooks/slack",
        json=payload,
    )

    assert response.status_code == 200

    response_data = response.json()
    assert response_data["success"] is True


@pytest.mark.asyncio
async def test_sentry_webhook_complete_flow(client: AsyncClient):
    payload = {
        "action": "created",
        "data": {"issue": {"title": "Error occurred"}},
        "actor": {"name": "test-user"},
    }

    response = await client.post(
        "/webhooks/sentry",
        json=payload,
    )

    assert response.status_code == 200

    response_data = response.json()
    assert response_data["success"] is True
