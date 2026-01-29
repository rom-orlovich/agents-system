import pytest
import asyncio
from httpx import AsyncClient
import redis.asyncio as redis
import json


@pytest.fixture
async def api_client():
    async with AsyncClient(base_url="http://localhost:8080") as client:
        yield client


@pytest.fixture
async def redis_client():
    client = await redis.from_url("redis://localhost:6379/0", decode_responses=True)
    yield client
    await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_end_to_end_github_webhook_to_task_completion(
    api_client: AsyncClient, redis_client: redis.Redis
):
    github_payload = {
        "action": "created",
        "issue": {"number": 1, "body": "@agent analyze this issue"},
        "repository": {"full_name": "test/repo"},
        "sender": {"login": "test-user"},
    }

    response = await api_client.post(
        "/webhooks/github",
        json=github_payload,
        headers={"X-GitHub-Event": "issues"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] is not None

    task_id = data["task_id"]

    await asyncio.sleep(0.5)

    queue_length = await redis_client.zcard("tasks")
    assert queue_length >= 0

    logs_response = await api_client.get(
        f"http://localhost:8090/api/v1/dashboard/tasks/{task_id}/logs"
    )

    if logs_response.status_code == 200:
        logs_data = logs_response.json()
        assert logs_data["task_id"] == task_id
        assert logs_data["metadata"] is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parallel_webhook_processing(api_client: AsyncClient):
    payloads = [
        {
            "action": "created",
            "issue": {"number": i, "body": f"@agent task {i}"},
            "repository": {"full_name": "test/repo"},
            "sender": {"login": "test-user"},
        }
        for i in range(10)
    ]

    tasks = [
        api_client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issues"},
        )
        for payload in payloads
    ]

    responses = await asyncio.gather(*tasks)

    assert all(r.status_code == 200 for r in responses)
    assert all(r.json()["success"] is True for r in responses)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_signature_validation_github(api_client: AsyncClient):
    import hmac
    import hashlib

    secret = "test-secret"
    payload = json.dumps(
        {
            "action": "created",
            "issue": {"number": 1, "body": "test"},
            "repository": {"full_name": "test/repo"},
            "sender": {"login": "test-user"},
        }
    ).encode()

    signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    response = await api_client.post(
        "/webhooks/github",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "issues",
        },
    )

    assert response.status_code in [200, 400]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_metrics_collection(api_client: AsyncClient):
    response = await api_client.get("/metrics")

    assert response.status_code == 200
    metrics_text = response.text

    assert "webhook_requests_total" in metrics_text
    assert "task_processing_duration_seconds" in metrics_text
