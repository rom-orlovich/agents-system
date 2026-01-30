"""Integration tests for all API service health checks."""

import pytest
import httpx


@pytest.mark.integration
class TestAllServicesHealth:
    """Test health checks for all API services."""

    SERVICES = [
        ("GitHub API", "http://localhost:3001", "github-api"),
        ("Jira API", "http://localhost:3002", "jira-api"),
        ("Slack API", "http://localhost:3003", "slack-api"),
        ("Sentry API", "http://localhost:3004", "sentry-api"),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("service_name,base_url,expected_service", SERVICES)
    async def test_service_health(self, service_name: str, base_url: str, expected_service: str):
        """Test individual service health endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{base_url}/health", timeout=5.0)
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["service"] == expected_service
            except httpx.ConnectError:
                pytest.skip(f"{service_name} not running")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("service_name,base_url,expected_service", SERVICES)
    async def test_service_metrics(self, service_name: str, base_url: str, expected_service: str):
        """Test Prometheus metrics endpoint for each service."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{base_url}/metrics", timeout=5.0)
                assert response.status_code == 200
                assert len(response.text) > 0
            except httpx.ConnectError:
                pytest.skip(f"{service_name} not running")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("service_name,base_url,expected_service", SERVICES)
    async def test_service_auth_required(
        self, service_name: str, base_url: str, expected_service: str
    ):
        """Test that API endpoints require authentication."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{base_url}/api/test", timeout=5.0)
                assert response.status_code in [401, 404]
            except httpx.ConnectError:
                pytest.skip(f"{service_name} not running")
