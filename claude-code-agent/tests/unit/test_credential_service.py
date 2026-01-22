import pytest
from datetime import datetime, timedelta
from shared.machine_models import ClaudeCredentials, AuthStatus


class TestClaudeCredentials:
    """Test credential validation logic."""
    
    def test_valid_credentials(self):
        """Valid credentials return VALID status."""
        future_ts = int((datetime.utcnow() + timedelta(hours=2)).timestamp() * 1000)
        creds = ClaudeCredentials(
            access_token="valid_token_12345",
            refresh_token="refresh_token_12345",
            expires_at=future_ts,
        )
        assert creds.get_status() == AuthStatus.VALID
        assert not creds.is_expired
        assert not creds.needs_refresh
    
    def test_expired_credentials(self):
        """Expired credentials return EXPIRED status."""
        past_ts = int((datetime.utcnow() - timedelta(hours=1)).timestamp() * 1000)
        creds = ClaudeCredentials(
            access_token="expired_token_12345",
            refresh_token="refresh_token_12345",
            expires_at=past_ts,
        )
        assert creds.get_status() == AuthStatus.EXPIRED
        assert creds.is_expired
    
    def test_needs_refresh_credentials(self):
        """Credentials expiring within 30 min return REFRESH_NEEDED."""
        soon_ts = int((datetime.utcnow() + timedelta(minutes=15)).timestamp() * 1000)
        creds = ClaudeCredentials(
            access_token="soon_expired_token",
            refresh_token="refresh_token_12345",
            expires_at=soon_ts,
        )
        assert creds.get_status() == AuthStatus.REFRESH_NEEDED
        assert creds.needs_refresh
        assert not creds.is_expired
    
    def test_invalid_token_format(self):
        """Short tokens are rejected."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ClaudeCredentials(
                access_token="short",  # < 10 chars
                refresh_token="refresh_token_12345",
                expires_at=1234567890000,
            )
    
    def test_expires_at_datetime_conversion(self):
        """Expires_at milliseconds converts correctly to datetime."""
        ts_ms = 1700000000000  # Nov 14, 2023
        creds = ClaudeCredentials(
            access_token="test_token_12345",
            refresh_token="refresh_token_12345",
            expires_at=ts_ms,
        )
        expected_dt = datetime.fromtimestamp(ts_ms / 1000)
        assert creds.expires_at_datetime == expected_dt
