import pytest
from unittest.mock import AsyncMock
from core.result_poster import ResultPoster, WebhookProvider
from core.types import MCPClientProtocol


class MockMCPClient:
    def __init__(self):
        self.calls = []

    async def call_tool(self, name: str, arguments: dict) -> bool:
        self.calls.append({"name": name, "arguments": arguments})
        return True


@pytest.fixture
def mock_mcp_client():
    return MockMCPClient()


@pytest.fixture
def result_poster(mock_mcp_client):
    return ResultPoster(mock_mcp_client)


@pytest.mark.asyncio
async def test_post_github_pr_result(result_poster, mock_mcp_client):
    metadata = {
        "repository": "owner/repo",
        "action": "pull_request",
        "pr_number": 123,
    }

    success = await result_poster.post_result(
        WebhookProvider.GITHUB, metadata, "Test result"
    )

    assert success is True
    assert len(mock_mcp_client.calls) == 2
    assert mock_mcp_client.calls[0]["name"] == "github_post_pr_comment"
    assert mock_mcp_client.calls[1]["name"] == "github_add_pr_reaction"


@pytest.mark.asyncio
async def test_post_github_issue_result(result_poster, mock_mcp_client):
    metadata = {
        "repository": "owner/repo",
        "action": "issue",
        "issue_number": 456,
    }

    success = await result_poster.post_result(
        WebhookProvider.GITHUB, metadata, "Issue result"
    )

    assert success is True
    assert len(mock_mcp_client.calls) == 1
    assert mock_mcp_client.calls[0]["name"] == "github_post_issue_comment"


@pytest.mark.asyncio
async def test_post_jira_result(result_poster, mock_mcp_client):
    metadata = {"issue_key": "PROJ-123"}

    success = await result_poster.post_result(
        WebhookProvider.JIRA, metadata, "Jira result"
    )

    assert success is True
    assert len(mock_mcp_client.calls) == 1
    assert mock_mcp_client.calls[0]["name"] == "jira_add_comment"
    assert mock_mcp_client.calls[0]["arguments"]["issue_key"] == "PROJ-123"


@pytest.mark.asyncio
async def test_post_slack_result(result_poster, mock_mcp_client):
    metadata = {"channel": "C123456", "thread_ts": "1234567890.123456"}

    success = await result_poster.post_result(
        WebhookProvider.SLACK, metadata, "Slack result"
    )

    assert success is True
    assert len(mock_mcp_client.calls) == 1
    assert mock_mcp_client.calls[0]["name"] == "slack_post_message"


@pytest.mark.asyncio
async def test_post_sentry_result(result_poster, mock_mcp_client):
    metadata = {"issue_id": "789"}

    success = await result_poster.post_result(
        WebhookProvider.SENTRY, metadata, "Sentry result"
    )

    assert success is True
    assert len(mock_mcp_client.calls) == 1
    assert mock_mcp_client.calls[0]["name"] == "sentry_add_comment"


@pytest.mark.asyncio
async def test_post_result_with_invalid_github_metadata(result_poster):
    metadata = {"repository": "invalid"}

    success = await result_poster.post_result(
        WebhookProvider.GITHUB, metadata, "Result"
    )

    assert success is False


@pytest.mark.asyncio
async def test_post_result_with_missing_jira_key(result_poster):
    metadata = {}

    success = await result_poster.post_result(WebhookProvider.JIRA, metadata, "Result")

    assert success is False


@pytest.mark.asyncio
async def test_result_poster_accepts_protocol_type():
    mock_client = AsyncMock(spec=MCPClientProtocol)
    mock_client.call_tool.return_value = True

    poster = ResultPoster(mock_client)
    metadata = {"issue_key": "TEST-1"}

    success = await poster.post_result(WebhookProvider.JIRA, metadata, "Result")

    assert success is True
