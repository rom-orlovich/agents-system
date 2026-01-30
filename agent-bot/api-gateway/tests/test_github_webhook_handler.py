import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from api_gateway.webhooks.github_handler import GitHubWebhookHandler
from api_gateway.queue.redis_queue import TaskQueue
from api_gateway.core.models import WebhookResponse
from pathlib import Path
import tempfile
import fakeredis.aioredis


@pytest.fixture
async def redis_queue():
    fake_redis = await fakeredis.aioredis.FakeRedis.from_url("redis://localhost")
    queue = TaskQueue(redis_url="redis://localhost")
    queue.redis_client = fake_redis
    await queue.connect()
    yield queue
    await queue.disconnect()


@pytest.fixture
def temp_logs_dir():
    return Path(tempfile.mkdtemp())


@pytest.fixture
def github_handler(redis_queue: TaskQueue, temp_logs_dir: Path):
    return GitHubWebhookHandler(task_queue=redis_queue, logs_base_dir=temp_logs_dir)


@pytest.mark.asyncio
async def test_github_handler_processes_issue_comment(github_handler: GitHubWebhookHandler):
    payload = {
        "action": "created",
        "issue": {"number": 42, "body": "@agent analyze this issue"},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "test-user"},
    }

    response = await github_handler.handle(payload, headers={})

    assert response.success is True
    assert response.task_id is not None
    assert response.error is None


@pytest.mark.asyncio
async def test_github_handler_processes_pr_comment(github_handler: GitHubWebhookHandler):
    payload = {
        "action": "created",
        "pull_request": {"number": 10, "body": "@agent review this PR"},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "test-user"},
    }

    response = await github_handler.handle(payload, headers={})

    assert response.success is True
    assert response.task_id is not None


@pytest.mark.asyncio
async def test_github_handler_validates_signature(github_handler: GitHubWebhookHandler):
    github_handler.signature_validator = lambda p, s: False

    payload = {
        "action": "created",
        "issue": {"number": 42, "body": "test"},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "test-user"},
    }

    response = await github_handler.handle(payload, headers={"X-Hub-Signature-256": "invalid"})

    assert response.success is False
    assert response.error == "Invalid signature"


@pytest.mark.asyncio
async def test_github_handler_invalid_payload(github_handler: GitHubWebhookHandler):
    payload = {"invalid": "structure"}

    response = await github_handler.handle(payload, headers={})

    assert response.success is False
    assert "Invalid payload" in response.error


@pytest.mark.asyncio
async def test_github_handler_no_command_returns_success_without_task(github_handler: GitHubWebhookHandler):
    payload = {
        "action": "created",
        "issue": {"number": 42, "body": "regular comment without command"},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "test-user"},
    }

    response = await github_handler.handle(payload, headers={})

    assert response.success is True
    assert response.task_id is None
    assert "No command found" in response.message
