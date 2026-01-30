import pytest
from api_gateway.webhooks.jira_handler import JiraWebhookHandler
from api_gateway.queue.redis_queue import TaskQueue
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
def jira_handler(redis_queue: TaskQueue, temp_logs_dir: Path):
    return JiraWebhookHandler(task_queue=redis_queue, logs_base_dir=temp_logs_dir)


@pytest.mark.asyncio
async def test_jira_handler_processes_issue_created(jira_handler: JiraWebhookHandler):
    payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "PROJ-123",
            "fields": {"description": "@agent analyze this issue"},
        },
        "user": {"accountId": "user-123"},
    }

    response = await jira_handler.handle(payload, headers={})

    assert response.success is True
    assert response.task_id is not None


@pytest.mark.asyncio
async def test_jira_handler_processes_comment_created(jira_handler: JiraWebhookHandler):
    payload = {
        "webhookEvent": "comment_created",
        "issue": {"key": "PROJ-123", "fields": {}},
        "comment": {"body": "@agent review this"},
        "user": {"accountId": "user-123"},
    }

    response = await jira_handler.handle(payload, headers={})

    assert response.success is True
    assert response.task_id is not None


@pytest.mark.asyncio
async def test_jira_handler_invalid_payload(jira_handler: JiraWebhookHandler):
    payload = {"invalid": "structure"}

    response = await jira_handler.handle(payload, headers={})

    assert response.success is False
    assert "Invalid payload" in response.error


@pytest.mark.asyncio
async def test_jira_handler_no_command(jira_handler: JiraWebhookHandler):
    payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {"key": "PROJ-123", "fields": {"description": "Regular issue"}},
        "user": {"accountId": "user-123"},
    }

    response = await jira_handler.handle(payload, headers={})

    assert response.success is True
    assert response.task_id is None
