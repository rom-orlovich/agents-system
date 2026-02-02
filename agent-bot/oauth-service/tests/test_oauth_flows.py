import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from providers.github import GitHubOAuthProvider
from providers.slack import SlackOAuthProvider
from providers.jira import JiraOAuthProvider


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.base_url = "https://example.com"
    settings.github_app_id = "123456"
    settings.github_app_name = "test-app"
    settings.github_client_id = "test-client-id"
    settings.github_client_secret = "test-client-secret"
    settings.github_private_key = (
        "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
    )
    settings.slack_client_id = "slack-client-id"
    settings.slack_client_secret = "slack-client-secret"
    settings.jira_client_id = "jira-client-id"
    settings.jira_client_secret = "jira-client-secret"
    return settings


class TestGitHubOAuthProvider:
    def test_get_authorization_url(self, mock_settings):
        provider = GitHubOAuthProvider(mock_settings)
        url = provider.get_authorization_url("test-state")

        assert "https://github.com/apps/test-app/installations/new" in url
        assert "state=test-state" in url


class TestSlackOAuthProvider:
    def test_get_authorization_url(self, mock_settings):
        provider = SlackOAuthProvider(mock_settings)
        url = provider.get_authorization_url("test-state")

        assert "https://slack.com/oauth/v2/authorize" in url
        assert "client_id=slack-client-id" in url
        assert "state=test-state" in url
        assert "chat:write" in url

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, mock_settings):
        provider = SlackOAuthProvider(mock_settings)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "access_token": "xoxb-test-token",
            "scope": "chat:write,channels:read",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            tokens = await provider.exchange_code("test-code", "test-state")

            assert tokens.access_token == "xoxb-test-token"
            assert "chat:write" in tokens.scopes


class TestJiraOAuthProvider:
    def test_get_authorization_url(self, mock_settings):
        provider = JiraOAuthProvider(mock_settings)
        url = provider.get_authorization_url("test-state")

        assert "https://auth.atlassian.com/authorize" in url
        assert "client_id=jira-client-id" in url
        assert "state=test-state" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url

    def test_code_verifier_generation(self, mock_settings):
        provider = JiraOAuthProvider(mock_settings)
        verifier = provider._generate_code_verifier()

        assert len(verifier) > 20
        assert verifier.replace("-", "").replace("_", "").isalnum()

    def test_code_challenge_generation(self, mock_settings):
        provider = JiraOAuthProvider(mock_settings)
        verifier = "test-verifier-string"
        challenge = provider._generate_code_challenge(verifier)

        assert len(challenge) > 0
        assert challenge != verifier
