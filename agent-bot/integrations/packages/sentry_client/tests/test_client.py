import pytest
import respx
import httpx
from sentry_client import (
    SentryClient,
    AddCommentInput,
    AddCommentResponse,
    UpdateIssueStatusInput,
    UpdateIssueStatusResponse,
    GetIssueInput,
    SentryIssueResponse,
    AssignIssueInput,
    AssignIssueResponse,
    AddTagInput,
    AddTagResponse,
    SentryAuthenticationError,
    SentryNotFoundError,
    SentryValidationError,
    SentryRateLimitError,
    SentryServerError,
)


@pytest.fixture
def sentry_client():
    return SentryClient(
        auth_token="test-token", org_slug="test-org", project_slug="test-project"
    )


@pytest.mark.asyncio
@respx.mock
async def test_add_comment_success(sentry_client):
    input_data = AddCommentInput(issue_id="123456", comment="Test comment")

    respx.post("https://sentry.io/api/0/issues/123456/notes/").mock(
        return_value=httpx.Response(201, json={"id": "78910"})
    )

    response = await sentry_client.add_comment(input_data)

    assert response.success is True
    assert response.comment_id == "78910"
    assert "Successfully added comment" in response.message


@pytest.mark.asyncio
@respx.mock
async def test_add_comment_not_found(sentry_client):
    input_data = AddCommentInput(issue_id="999999", comment="Test comment")

    respx.post("https://sentry.io/api/0/issues/999999/notes/").mock(
        return_value=httpx.Response(404, json={"error": "Issue not found"})
    )

    with pytest.raises(SentryNotFoundError):
        await sentry_client.add_comment(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_add_comment_authentication_error(sentry_client):
    input_data = AddCommentInput(issue_id="123456", comment="Test comment")

    respx.post("https://sentry.io/api/0/issues/123456/notes/").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )

    with pytest.raises(SentryAuthenticationError):
        await sentry_client.add_comment(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_update_issue_status_success(sentry_client):
    input_data = UpdateIssueStatusInput(issue_id="123456", status="resolved")

    respx.put("https://sentry.io/api/0/issues/123456/").mock(
        return_value=httpx.Response(200, json={"status": "resolved"})
    )

    response = await sentry_client.update_issue_status(input_data)

    assert response.success is True
    assert "Successfully updated status" in response.message


@pytest.mark.asyncio
@respx.mock
async def test_update_issue_status_validation_error(sentry_client):
    input_data = UpdateIssueStatusInput(issue_id="123456", status="resolved")

    respx.put("https://sentry.io/api/0/issues/123456/").mock(
        return_value=httpx.Response(
            400, json={"error": "Invalid status"}
        )
    )

    with pytest.raises(SentryValidationError):
        await sentry_client.update_issue_status(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_get_issue_success(sentry_client):
    input_data = GetIssueInput(issue_id="123456")

    respx.get("https://sentry.io/api/0/issues/123456/").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "123456",
                "title": "Error in production",
                "status": "unresolved",
                "level": "error",
                "culprit": "main.py in handle_request",
            },
        )
    )

    response = await sentry_client.get_issue(input_data)

    assert response.success is True
    assert response.issue_id == "123456"
    assert response.title == "Error in production"
    assert response.status == "unresolved"
    assert response.level == "error"


@pytest.mark.asyncio
@respx.mock
async def test_get_issue_not_found(sentry_client):
    input_data = GetIssueInput(issue_id="999999")

    respx.get("https://sentry.io/api/0/issues/999999/").mock(
        return_value=httpx.Response(404, json={"error": "Issue not found"})
    )

    with pytest.raises(SentryNotFoundError):
        await sentry_client.get_issue(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_assign_issue_success(sentry_client):
    input_data = AssignIssueInput(issue_id="123456", assignee="dev@example.com")

    respx.put("https://sentry.io/api/0/issues/123456/").mock(
        return_value=httpx.Response(200, json={"assignedTo": "dev@example.com"})
    )

    response = await sentry_client.assign_issue(input_data)

    assert response.success is True
    assert "Successfully assigned issue" in response.message


@pytest.mark.asyncio
@respx.mock
async def test_assign_issue_rate_limit(sentry_client):
    input_data = AssignIssueInput(issue_id="123456", assignee="dev@example.com")

    respx.put("https://sentry.io/api/0/issues/123456/").mock(
        return_value=httpx.Response(429, json={"error": "Rate limit exceeded"})
    )

    with pytest.raises(SentryRateLimitError):
        await sentry_client.assign_issue(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_add_tag_success(sentry_client):
    input_data = AddTagInput(issue_id="123456", key="environment", value="production")

    respx.post("https://sentry.io/api/0/issues/123456/tags/").mock(
        return_value=httpx.Response(201, json={"key": "environment", "value": "production"})
    )

    response = await sentry_client.add_tag(input_data)

    assert response.success is True
    assert "Successfully added tag" in response.message


@pytest.mark.asyncio
@respx.mock
async def test_add_tag_server_error(sentry_client):
    input_data = AddTagInput(issue_id="123456", key="environment", value="production")

    respx.post("https://sentry.io/api/0/issues/123456/tags/").mock(
        return_value=httpx.Response(500, json={"error": "Internal server error"})
    )

    with pytest.raises(SentryServerError):
        await sentry_client.add_tag(input_data)


@pytest.mark.asyncio
async def test_pydantic_strict_validation():
    with pytest.raises(ValueError):
        AddCommentInput(issue_id="123456", comment=123)

    with pytest.raises(ValueError):
        UpdateIssueStatusInput(issue_id="123456", status="invalid_status")

    with pytest.raises(ValueError):
        AssignIssueInput(issue_id=None, assignee="dev@example.com")
