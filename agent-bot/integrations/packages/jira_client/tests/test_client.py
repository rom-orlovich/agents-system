import pytest
import respx
import httpx
from jira_client import (
    JiraClient,
    AddCommentInput,
    AddCommentResponse,
    GetIssueInput,
    JiraIssueResponse,
    CreateIssueInput,
    CreateIssueResponse,
    TransitionIssueInput,
    TransitionIssueResponse,
    JiraAuthenticationError,
    JiraNotFoundError,
    JiraValidationError,
    JiraRateLimitError,
    JiraServerError,
)


@pytest.fixture
def jira_client():
    return JiraClient(
        email="test@example.com",
        api_token="test-token",
        domain="example.atlassian.net",
    )


@pytest.mark.asyncio
@respx.mock
async def test_add_comment_success(jira_client):
    input_data = AddCommentInput(issue_key="PROJ-123", comment="Test comment")

    respx.post("https://example.atlassian.net/rest/api/3/issue/PROJ-123/comment").mock(
        return_value=httpx.Response(200, json={"id": "12345"})
    )

    response = await jira_client.add_comment(input_data)

    assert response.success is True
    assert response.comment_id == "12345"
    assert "Successfully added comment" in response.message


@pytest.mark.asyncio
@respx.mock
async def test_add_comment_not_found(jira_client):
    input_data = AddCommentInput(issue_key="PROJ-999", comment="Test comment")

    respx.post("https://example.atlassian.net/rest/api/3/issue/PROJ-999/comment").mock(
        return_value=httpx.Response(404, json={"error": "Issue not found"})
    )

    with pytest.raises(JiraNotFoundError):
        await jira_client.add_comment(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_add_comment_authentication_error(jira_client):
    input_data = AddCommentInput(issue_key="PROJ-123", comment="Test comment")

    respx.post("https://example.atlassian.net/rest/api/3/issue/PROJ-123/comment").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )

    with pytest.raises(JiraAuthenticationError):
        await jira_client.add_comment(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_add_comment_rate_limit(jira_client):
    input_data = AddCommentInput(issue_key="PROJ-123", comment="Test comment")

    respx.post("https://example.atlassian.net/rest/api/3/issue/PROJ-123/comment").mock(
        return_value=httpx.Response(429, json={"error": "Rate limit exceeded"})
    )

    with pytest.raises(JiraRateLimitError):
        await jira_client.add_comment(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_get_issue_success(jira_client):
    input_data = GetIssueInput(issue_key="PROJ-123")

    respx.get("https://example.atlassian.net/rest/api/3/issue/PROJ-123").mock(
        return_value=httpx.Response(
            200,
            json={
                "key": "PROJ-123",
                "fields": {
                    "summary": "Test Issue",
                    "status": {"name": "In Progress"},
                    "description": "Test description",
                },
            },
        )
    )

    response = await jira_client.get_issue(input_data)

    assert response.success is True
    assert response.issue_key == "PROJ-123"
    assert response.title == "Test Issue"
    assert response.status == "In Progress"
    assert response.description == "Test description"


@pytest.mark.asyncio
@respx.mock
async def test_get_issue_not_found(jira_client):
    input_data = GetIssueInput(issue_key="PROJ-999")

    respx.get("https://example.atlassian.net/rest/api/3/issue/PROJ-999").mock(
        return_value=httpx.Response(404, json={"error": "Issue not found"})
    )

    with pytest.raises(JiraNotFoundError):
        await jira_client.get_issue(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_create_issue_success(jira_client):
    input_data = CreateIssueInput(
        project_key="PROJ",
        summary="New Issue",
        description="Issue description",
        issue_type="Task",
    )

    respx.post("https://example.atlassian.net/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-456"})
    )

    response = await jira_client.create_issue(input_data)

    assert response.success is True
    assert response.issue_key == "PROJ-456"
    assert "Successfully created issue" in response.message


@pytest.mark.asyncio
@respx.mock
async def test_create_issue_validation_error(jira_client):
    input_data = CreateIssueInput(
        project_key="INVALID",
        summary="New Issue",
        description="Issue description",
        issue_type="Task",
    )

    respx.post("https://example.atlassian.net/rest/api/3/issue").mock(
        return_value=httpx.Response(
            400, json={"error": "Project does not exist"}
        )
    )

    with pytest.raises(JiraValidationError):
        await jira_client.create_issue(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_transition_issue_success(jira_client):
    input_data = TransitionIssueInput(issue_key="PROJ-123", transition_id="31")

    respx.post(
        "https://example.atlassian.net/rest/api/3/issue/PROJ-123/transitions"
    ).mock(return_value=httpx.Response(204))

    response = await jira_client.transition_issue(input_data)

    assert response.success is True
    assert "Successfully transitioned" in response.message


@pytest.mark.asyncio
@respx.mock
async def test_transition_issue_server_error(jira_client):
    input_data = TransitionIssueInput(issue_key="PROJ-123", transition_id="31")

    respx.post(
        "https://example.atlassian.net/rest/api/3/issue/PROJ-123/transitions"
    ).mock(return_value=httpx.Response(500, json={"error": "Internal server error"}))

    with pytest.raises(JiraServerError):
        await jira_client.transition_issue(input_data)


@pytest.mark.asyncio
async def test_pydantic_strict_validation():
    with pytest.raises(ValueError):
        AddCommentInput(issue_key="PROJ-123", comment=123)

    with pytest.raises(ValueError):
        AddCommentInput(issue_key=None, comment="Test")

    with pytest.raises(ValueError):
        CreateIssueInput(
            project_key="PROJ",
            summary="Test",
            description="Test",
            issue_type=None,
        )
