import pytest
from httpx import AsyncClient
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


@pytest.mark.integration
class TestCredentialsAPI:
    """Integration tests for credential endpoints."""
    
    async def test_status_missing_credentials(self, client: AsyncClient, tmp_path, monkeypatch):
        """Status returns MISSING when no credentials file."""
        # Set DATA_DIR to tmp_path so credentials_path points to tmp location
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        # Reload settings to pick up new env var
        from core.config import Settings
        test_settings = Settings()
        
        with patch('api.credentials.settings', test_settings):
            response = await client.get("/api/credentials/status")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["missing", "cli_unavailable"]
            assert "cli_available" in data
    
    async def test_upload_valid_credentials(self, client: AsyncClient, tmp_path, monkeypatch):
        """Upload valid credentials file succeeds."""
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        from core.config import Settings
        test_settings = Settings()
        
        with patch('api.credentials.settings', test_settings):
            future_ts = int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp() * 1000)
            creds_content = json.dumps({
                "access_token": "valid_access_token_12345",
                "refresh_token": "valid_refresh_token_12345",
                "expires_at": future_ts,
            })
            
            response = await client.post(
                "/api/credentials/upload",
                files={"file": ("claude.json", creds_content, "application/json")}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "expires_at" in data["data"]
    
    async def test_upload_expired_credentials_rejected(self, client: AsyncClient, tmp_path, monkeypatch):
        """Upload expired credentials is rejected."""
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        from core.config import Settings
        test_settings = Settings()
        
        with patch('api.credentials.settings', test_settings):
            past_ts = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000)
            creds_content = json.dumps({
                "access_token": "expired_access_token_12345",
                "refresh_token": "expired_refresh_token_12345",
                "expires_at": past_ts,
            })
            
            response = await client.post(
                "/api/credentials/upload",
                files={"file": ("claude.json", creds_content, "application/json")}
            )
            assert response.status_code == 400
            assert "expired" in response.json()["detail"].lower()
    
    async def test_upload_invalid_json_rejected(self, client: AsyncClient, tmp_path, monkeypatch):
        """Upload invalid JSON is rejected."""
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        from core.config import Settings
        test_settings = Settings()
        
        with patch('api.credentials.settings', test_settings):
            response = await client.post(
                "/api/credentials/upload",
                files={"file": ("claude.json", "not valid json", "application/json")}
            )
            assert response.status_code == 400
    
    async def test_upload_non_json_file_rejected(self, client: AsyncClient, tmp_path, monkeypatch):
        """Upload non-JSON file is rejected."""
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        from core.config import Settings
        test_settings = Settings()
        
        with patch('api.credentials.settings', test_settings):
            response = await client.post(
                "/api/credentials/upload",
                files={"file": ("credentials.txt", "some text", "text/plain")}
            )
            assert response.status_code == 400
    
    async def test_status_valid_credentials(self, client: AsyncClient, tmp_path, monkeypatch):
        """Status returns VALID when credentials are valid."""
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        from core.config import Settings
        test_settings = Settings()
        
        # Create credentials file
        creds_path = test_settings.credentials_path
        creds_path.parent.mkdir(parents=True, exist_ok=True)
        
        future_ts = int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp() * 1000)
        creds_content = {
            "access_token": "valid_access_token_12345",
            "refresh_token": "valid_refresh_token_12345",
            "expires_at": future_ts,
        }
        creds_path.write_text(json.dumps(creds_content))
        
        with patch('api.credentials.settings', test_settings):
            response = await client.get("/api/credentials/status")
            assert response.status_code == 200
            data = response.json()
            if data.get("cli_available"):
                assert data["status"] in ["valid", "refresh_needed"]
