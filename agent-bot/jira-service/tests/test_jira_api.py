import pytest
from httpx import AsyncClient
from main import app
import respx
from httpx import Response


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
    assert data["service"] == "jira-service"


@pytest.mark.asyncio
@respx.mock
async def test_add_comment_success(client: AsyncClient):
    respx.post("https://test.atlassian.net/rest/api/3/issue/PROJ-123/comment").mock(
        return_value=Response(201, json={"id": "10001"})
    )

    payload = {"issue_key": "PROJ-123", "comment": "Test comment"}

    response = await client.post("/api/v1/jira/issue/PROJ-123/comment", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["comment_id"] == "10001"


@pytest.mark.asyncio
@respx.mock
async def test_get_issue_success(client: AsyncClient):
    respx.get("https://test.atlassian.net/rest/api/3/issue/PROJ-123").mock(
        return_value=Response(
            200,
            json={
                "key": "PROJ-123",
                "fields": {
                    "summary": "Test issue",
                    "description": "Test description",
                    "status": {"name": "Open"},
                    "assignee": {"displayName": "John Doe"},
                    "reporter": {"displayName": "Jane Smith"},
                },
            },
        )
    )

    response = await client.get("/api/v1/jira/issue/PROJ-123")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["issue_key"] == "PROJ-123"
    assert data["summary"] == "Test issue"


@pytest.mark.asyncio
@respx.mock
async def test_create_issue_success(client: AsyncClient):
    respx.post("https://test.atlassian.net/rest/api/3/issue").mock(
        return_value=Response(201, json={"key": "PROJ-124", "id": "10002"})
    )

    payload = {
        "project_key": "PROJ",
        "summary": "New issue",
        "description": "Issue description",
        "issue_type": "Bug",
    }

    response = await client.post("/api/v1/jira/issue", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["issue_key"] == "PROJ-124"
