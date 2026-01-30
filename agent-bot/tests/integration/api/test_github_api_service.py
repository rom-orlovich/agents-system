"""Integration tests for GitHub API service."""

import pytest
import httpx


@pytest.mark.integration
class TestGitHubAPIService:
    """Test GitHub API service integration."""

    BASE_URL = "http://localhost:3001"

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "github-api"

    @pytest.mark.asyncio
    async def test_missing_auth_header(self):
        """Test request without auth header."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}/api/repos/owner/repo")
            assert response.status_code == 401
            data = response.json()
            assert "Authorization" in data["detail"]

    @pytest.mark.asyncio
    async def test_invalid_auth_format(self):
        """Test request with invalid auth format."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/api/repos/owner/repo",
                headers={"Authorization": "InvalidFormat token123"},
            )
            assert response.status_code == 401
            data = response.json()
            assert "Invalid Authorization format" in data["detail"]

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """Test request with invalid token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/api/repos/owner/repo",
                headers={"Authorization": "Bearer invalid_token_123"},
            )
            assert response.status_code == 401
            data = response.json()
            assert "Invalid token" in data["detail"]

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting middleware."""
        async with httpx.AsyncClient() as client:
            responses = []
            for _ in range(15):
                response = await client.get(
                    f"{self.BASE_URL}/api/repos/owner/repo",
                    headers={"Authorization": "Bearer test_token"},
                )
                responses.append(response.status_code)

            assert 429 in responses

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}/metrics")
            assert response.status_code == 200
            assert "github_api" in response.text or "process_" in response.text
