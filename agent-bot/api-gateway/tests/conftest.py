"""API Gateway test fixtures."""

import hashlib
import hmac
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests"))

from fixtures import (
    github_issue_opened_payload,
    github_issue_comment_payload,
    github_pr_opened_payload,
    jira_issue_created_payload,
    jira_comment_created_payload,
    slack_app_mention_payload,
    sentry_issue_created_payload,
)


@pytest.fixture
def mock_gateway_settings():
    """Mock settings for API gateway."""
    settings = MagicMock()
    settings.redis_url = "redis://localhost:6379/0"
    settings.github_webhook_secret = "test-github-secret"
    settings.jira_webhook_secret = "test-jira-secret"
    settings.slack_signing_secret = "test-slack-secret"
    settings.sentry_webhook_secret = "test-sentry-secret"
    settings.port = 8000
    return settings


@pytest.fixture
def github_signature_generator():
    """Generate valid GitHub webhook signatures."""
    def _generate(payload: bytes, secret: str) -> str:
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    return _generate


@pytest.fixture
def jira_signature_generator():
    """Generate valid Jira webhook signatures."""
    def _generate(payload: bytes, secret: str) -> str:
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    return _generate


@pytest.fixture
def slack_signature_generator():
    """Generate valid Slack webhook signatures."""
    def _generate(payload: bytes, secret: str, timestamp: str) -> tuple[str, str]:
        sig_basestring = f"v0:{timestamp}:{payload.decode()}"
        signature = hmac.new(
            secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"v0={signature}", timestamp
    return _generate


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for webhook tests."""
    redis = MagicMock()
    redis.lpush = AsyncMock(return_value=1)
    redis.aclose = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    return redis
