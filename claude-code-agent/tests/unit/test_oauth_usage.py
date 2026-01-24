"""Tests for OAuth usage tracking."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from core.oauth_usage import (
    fetch_oauth_usage,
    SessionUsage,
    WeeklyUsage,
    OAuthUsageResponse,
    load_credentials,
)
from shared.machine_models import ClaudeCredentials


@pytest.fixture
def mock_credentials():
    """Mock valid credentials."""
    import time
    expires_at = int((time.time() + 3600) * 1000)  # 1 hour from now
    return ClaudeCredentials(
        access_token="test_token_12345",
        refresh_token="refresh_token_12345",
        expires_at=expires_at,
        token_type="Bearer",
        account_id="test_account_123",
    )


@pytest.fixture
def mock_expired_credentials():
    """Mock expired credentials."""
    import time
    expires_at = int((time.time() - 3600) * 1000)  # 1 hour ago
    return ClaudeCredentials(
        access_token="expired_token",
        refresh_token="expired_refresh",
        expires_at=expires_at,
        token_type="Bearer",
    )


class TestSessionUsage:
    """Test SessionUsage model."""
    
    def test_session_usage_calculation(self):
        """Test session usage calculations."""
        usage = SessionUsage(used=45, limit=50)
        assert usage.remaining == 5
        assert usage.percentage == 90.0
        assert usage.is_exceeded is False
    
    def test_session_usage_exceeded(self):
        """Test exceeded session usage."""
        usage = SessionUsage(used=50, limit=50)
        assert usage.remaining == 0
        assert usage.percentage == 100.0
        assert usage.is_exceeded is True
    
    def test_session_usage_zero_limit(self):
        """Test zero limit handling."""
        usage = SessionUsage(used=0, limit=0)
        assert usage.percentage == 0.0
        assert usage.remaining == 0


class TestWeeklyUsage:
    """Test WeeklyUsage model."""
    
    def test_weekly_usage_calculation(self):
        """Test weekly usage calculations."""
        usage = WeeklyUsage(used=200, limit=500)
        assert usage.remaining == 300
        assert usage.percentage == 40.0
        assert usage.is_exceeded is False


class TestLoadCredentials:
    """Test credential loading."""
    
    @patch("core.oauth_usage.settings")
    @patch("pathlib.Path.read_text")
    @patch("json.loads")
    def test_load_credentials_success(self, mock_json_loads, mock_read_text, mock_settings):
        """Test successful credential loading."""
        mock_settings.credentials_path = MagicMock()
        mock_settings.credentials_path.exists.return_value = True
        mock_json_loads.return_value = {
            "access_token": "test_token",
            "refresh_token": "test_refresh",
            "expires_at": 1234567890000,
        }
        mock_read_text.return_value = '{"access_token": "test"}'
        
        creds = load_credentials()
        assert creds is not None
        assert isinstance(creds, ClaudeCredentials)
    
    @patch("core.oauth_usage.settings")
    def test_load_credentials_not_found(self, mock_settings):
        """Test when credentials file doesn't exist."""
        mock_settings.credentials_path = MagicMock()
        mock_settings.credentials_path.exists.return_value = False
        
        creds = load_credentials()
        assert creds is None


class TestFetchOAuthUsage:
    """Test OAuth usage fetching."""
    
    @pytest.mark.asyncio
    @patch("core.oauth_usage.load_credentials")
    async def test_fetch_no_credentials(self, mock_load_creds):
        """Test when no credentials are available."""
        mock_load_creds.return_value = None
        
        result = await fetch_oauth_usage()
        
        assert isinstance(result, OAuthUsageResponse)
        assert result.error is not None
        assert "No credentials found" in result.error
        assert result.session is None
        assert result.weekly is None
    
    @pytest.mark.asyncio
    @patch("core.oauth_usage.load_credentials")
    async def test_fetch_expired_credentials(self, mock_load_creds, mock_expired_credentials):
        """Test when credentials are expired."""
        mock_load_creds.return_value = mock_expired_credentials
        
        result = await fetch_oauth_usage()
        
        assert isinstance(result, OAuthUsageResponse)
        assert result.error is not None
        assert "expired" in result.error.lower()
    
    @pytest.mark.asyncio
    @patch("core.oauth_usage.load_credentials")
    @patch("httpx.AsyncClient")
    async def test_fetch_success(self, mock_client_class, mock_load_creds, mock_credentials):
        """Test successful usage fetch."""
        mock_load_creds.return_value = mock_credentials
        
        # Mock successful API response (httpx response.json() is synchronous)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "session": {"used": 45, "limit": 50},
            "weekly": {"used": 200, "limit": 500},
        }
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        result = await fetch_oauth_usage()
        
        assert isinstance(result, OAuthUsageResponse)
        assert result.error is None
        assert result.session is not None
        assert result.session.used == 45
        assert result.session.limit == 50
        assert result.weekly is not None
        assert result.weekly.used == 200
        assert result.weekly.limit == 500
    
    @pytest.mark.asyncio
    @patch("core.oauth_usage.load_credentials")
    @patch("httpx.AsyncClient")
    async def test_fetch_401_tries_next_method(self, mock_client_class, mock_load_creds, mock_credentials):
        """Test that 401 responses try next authentication method."""
        mock_load_creds.return_value = mock_credentials
        
        # First attempt returns 401, second succeeds
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"session": {"used": 10, "limit": 50}}
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get = AsyncMock(side_effect=[mock_response_401, mock_response_200])
        mock_client_class.return_value = mock_client
        
        result = await fetch_oauth_usage()
        
        # Should succeed on second attempt
        assert result.error is None
        assert result.session is not None
        assert mock_client.get.call_count == 2  # Tried two methods
    
    @pytest.mark.asyncio
    @patch("core.oauth_usage.load_credentials")
    @patch("httpx.AsyncClient")
    async def test_fetch_404_error(self, mock_client_class, mock_load_creds, mock_credentials):
        """Test 404 error handling."""
        mock_load_creds.return_value = mock_credentials
        
        mock_response = AsyncMock()
        mock_response.status_code = 404
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = await fetch_oauth_usage()
        
        assert result.error is not None
        assert "404" in result.error or "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    @patch("core.oauth_usage.load_credentials")
    @patch("httpx.AsyncClient")
    async def test_fetch_timeout(self, mock_client_class, mock_load_creds, mock_credentials):
        """Test timeout handling."""
        mock_load_creds.return_value = mock_credentials
        
        import httpx
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        mock_client_class.return_value = mock_client
        
        result = await fetch_oauth_usage()
        
        # Should try all methods, then return error
        assert result.error is not None
