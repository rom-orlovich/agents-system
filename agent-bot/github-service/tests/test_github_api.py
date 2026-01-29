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
    assert data["service"] == "github-service"


@pytest.mark.asyncio
@respx.mock
async def test_post_pr_comment_success(client: AsyncClient):
    respx.post("https://api.github.com/repos/owner/repo/issues/1/comments").mock(
        return_value=Response(200, json={"id": 123, "body": "test comment"})
    )

    payload = {
        "owner": "owner",
        "repo": "repo",
        "pr_number": 1,
        "comment": "test comment",
    }

    response = await client.post("/api/v1/github/pr/owner/repo/1/comment", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["comment_id"] == 123


@pytest.mark.asyncio
async def test_post_pr_comment_invalid_schema(client: AsyncClient):
    payload = {"invalid": "payload"}

    response = await client.post("/api/v1/github/pr/owner/repo/1/comment", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
@respx.mock
async def test_get_pr_details(client: AsyncClient):
    respx.get("https://api.github.com/repos/owner/repo/pulls/1").mock(
        return_value=Response(
            200,
            json={
                "number": 1,
                "title": "Test PR",
                "body": "Test description",
                "state": "open",
                "merged": False,
            },
        )
    )

    response = await client.get("/api/v1/github/pr/owner/repo/1")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["pr_number"] == 1
    assert data["title"] == "Test PR"
