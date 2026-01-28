"""TDD tests for routing.py → metadata.py rename (Phases 6-8)."""

import pytest


class TestGitHubMetadataRename:
    """Test GitHub routing.py renamed to metadata.py."""

    def test_can_import_from_github_metadata(self):
        """extract_github_routing should be importable from github.metadata."""
        from api.webhooks.github.metadata import extract_github_routing

        assert callable(extract_github_routing)

    def test_cannot_import_from_github_routing(self):
        """Importing from github.routing should fail."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            from api.webhooks.github.routing import extract_github_routing


class TestJiraMetadataRename:
    """Test Jira routing.py renamed to metadata.py."""

    def test_can_import_from_jira_metadata(self):
        """extract_jira_routing should be importable from jira.metadata."""
        from api.webhooks.jira.metadata import extract_jira_routing

        assert callable(extract_jira_routing)

    def test_cannot_import_from_jira_routing(self):
        """Importing from jira.routing should fail."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            from api.webhooks.jira.routing import extract_jira_routing


class TestSlackMetadataRename:
    """Test Slack routing.py renamed to metadata.py."""

    def test_can_import_from_slack_metadata(self):
        """extract_slack_routing should be importable from slack.metadata."""
        from api.webhooks.slack.metadata import extract_slack_routing

        assert callable(extract_slack_routing)

    def test_cannot_import_from_slack_routing(self):
        """Importing from slack.routing should fail."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            from api.webhooks.slack.routing import extract_slack_routing
