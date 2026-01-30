"""Tests for GitHub client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import sys
sys.path.insert(0, "integrations/packages")

from github_client import GitHubClient, GitHubAuthError, GitHubNotFoundError
from github_client.models import Repository, PullRequest, User


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    response = MagicMock()
    response.status_code = 200
    response.json = MagicMock(return_value={
        "id": 123,
        "name": "test-repo",
        "full_name": "owner/test-repo",
        "owner": {
            "login": "owner",
            "id": 1,
            "avatar_url": "https://example.com/avatar.png",
            "url": "https://api.github.com/users/owner",
        },
        "html_url": "https://github.com/owner/test-repo",
        "private": False,
        "default_branch": "main",
    })
    return response


@pytest.mark.asyncio
async def test_github_client_context_manager():
    """Test GitHub client async context manager."""
    client = GitHubClient(token="test-token")

    async with client as c:
        assert c._client is not None

    assert client._client is None or client._client.is_closed


@pytest.mark.asyncio
async def test_get_repository_success(mock_response):
    """Test successful repository retrieval."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        async with GitHubClient(token="test-token") as client:
            repo = await client.get_repository("owner", "test-repo")

        assert isinstance(repo, Repository)
        assert repo.name == "test-repo"
        assert repo.full_name == "owner/test-repo"


@pytest.mark.asyncio
async def test_github_auth_error():
    """Test GitHub authentication error."""
    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        async with GitHubClient(token="invalid-token") as client:
            with pytest.raises(GitHubAuthError):
                await client.get_repository("owner", "repo")


@pytest.mark.asyncio
async def test_github_not_found_error():
    """Test GitHub not found error."""
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        async with GitHubClient(token="test-token") as client:
            with pytest.raises(GitHubNotFoundError):
                await client.get_repository("owner", "nonexistent")
