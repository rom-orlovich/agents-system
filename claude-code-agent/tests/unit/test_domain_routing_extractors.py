"""TDD tests for domain routing extractors (Phase 6.1)."""

import pytest
from api.webhooks.github.models import GitHubRoutingMetadata
from api.webhooks.jira.models import JiraRoutingMetadata
from api.webhooks.slack.models import SlackRoutingMetadata


class TestGitHubRoutingExtractor:
    """Test GitHub domain routing extractor."""

    def test_extracts_owner_and_repo_from_full_name(self):
        """
        Business Rule: Extracts owner and repo from repository.full_name.
        Behavior: Splits "owner/repo" into separate fields.
        """
        from api.webhooks.github.routing import extract_github_routing

        payload = {
            "repository": {"full_name": "test-owner/test-repo"},
            "issue": {"number": 123}
        }

        routing = extract_github_routing(payload)

        assert isinstance(routing, GitHubRoutingMetadata)
        assert routing.owner == "test-owner"
        assert routing.repo == "test-repo"

    def test_extracts_issue_number(self):
        """
        Business Rule: Extracts issue number from issue events.
        Behavior: Returns issue_number from payload.issue.number.
        """
        from api.webhooks.github.routing import extract_github_routing

        payload = {
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 456}
        }

        routing = extract_github_routing(payload)

        assert routing.issue_number == 456

    def test_extracts_pr_number_from_pull_request(self):
        """
        Business Rule: Extracts PR number from pull_request events.
        Behavior: Returns pr_number from payload.pull_request.number.
        """
        from api.webhooks.github.routing import extract_github_routing

        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 789}
        }

        routing = extract_github_routing(payload)

        assert routing.pr_number == 789

    def test_detects_pr_from_issue_with_pull_request_key(self):
        """
        Business Rule: Detects PR from issue that has pull_request key.
        Behavior: When issue has pull_request field, sets pr_number.
        """
        from api.webhooks.github.routing import extract_github_routing

        payload = {
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 111, "pull_request": {"url": "https://..."}}
        }

        routing = extract_github_routing(payload)

        assert routing.pr_number == 111

    def test_extracts_comment_id(self):
        """
        Business Rule: Extracts comment ID from comment events.
        Behavior: Returns comment_id from payload.comment.id.
        """
        from api.webhooks.github.routing import extract_github_routing

        payload = {
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123},
            "comment": {"id": 999}
        }

        routing = extract_github_routing(payload)

        assert routing.comment_id == 999

    def test_extracts_sender_login(self):
        """
        Business Rule: Extracts sender username from sender.login.
        Behavior: Returns sender from payload.sender.login.
        """
        from api.webhooks.github.routing import extract_github_routing

        payload = {
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123},
            "sender": {"login": "contributor"}
        }

        routing = extract_github_routing(payload)

        assert routing.sender == "contributor"

    def test_returns_pydantic_model(self):
        """
        Business Rule: Returns strict Pydantic model.
        Behavior: Return type is GitHubRoutingMetadata.
        """
        from api.webhooks.github.routing import extract_github_routing

        payload = {
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123}
        }

        routing = extract_github_routing(payload)

        assert isinstance(routing, GitHubRoutingMetadata)

    def test_handles_missing_repository(self):
        """
        Business Rule: Handles payloads without repository gracefully.
        Behavior: Returns model with empty owner/repo.
        """
        from api.webhooks.github.routing import extract_github_routing

        payload = {"issue": {"number": 123}}

        routing = extract_github_routing(payload)

        assert routing.owner == ""
        assert routing.repo == ""


class TestJiraRoutingExtractor:
    """Test Jira domain routing extractor."""

    def test_extracts_issue_key(self):
        """
        Business Rule: Extracts ticket key from issue.key.
        Behavior: Returns issue_key from payload.issue.key.
        """
        from api.webhooks.jira.routing import extract_jira_routing

        payload = {
            "issue": {"key": "PROJ-123"}
        }

        routing = extract_jira_routing(payload)

        assert isinstance(routing, JiraRoutingMetadata)
        assert routing.issue_key == "PROJ-123"

    def test_extracts_project_key_from_issue_key(self):
        """
        Business Rule: Extracts project key from ticket key.
        Behavior: Parses project from "PROJ-123" format.
        """
        from api.webhooks.jira.routing import extract_jira_routing

        payload = {
            "issue": {"key": "MYPROJ-456"}
        }

        routing = extract_jira_routing(payload)

        assert routing.project_key == "MYPROJ"

    def test_extracts_project_key_from_fields(self):
        """
        Business Rule: Extracts project key from fields.project.key.
        Behavior: Uses fields.project.key as authoritative source.
        """
        from api.webhooks.jira.routing import extract_jira_routing

        payload = {
            "issue": {
                "key": "PROJ-123",
                "fields": {"project": {"key": "REALPROJ"}}
            }
        }

        routing = extract_jira_routing(payload)

        assert routing.project_key == "REALPROJ"

    def test_extracts_comment_id(self):
        """
        Business Rule: Extracts comment ID from comment events.
        Behavior: Returns comment_id from payload.comment.id.
        """
        from api.webhooks.jira.routing import extract_jira_routing

        payload = {
            "issue": {"key": "PROJ-123"},
            "comment": {"id": "12345"}
        }

        routing = extract_jira_routing(payload)

        assert routing.comment_id == "12345"

    def test_extracts_user_name(self):
        """
        Business Rule: Extracts user name from user field.
        Behavior: Returns user_name from payload.user.displayName.
        """
        from api.webhooks.jira.routing import extract_jira_routing

        payload = {
            "issue": {"key": "PROJ-123"},
            "user": {"displayName": "John Doe"}
        }

        routing = extract_jira_routing(payload)

        assert routing.user_name == "John Doe"

    def test_returns_pydantic_model(self):
        """
        Business Rule: Returns strict Pydantic model.
        Behavior: Return type is JiraRoutingMetadata.
        """
        from api.webhooks.jira.routing import extract_jira_routing

        payload = {"issue": {"key": "PROJ-123"}}

        routing = extract_jira_routing(payload)

        assert isinstance(routing, JiraRoutingMetadata)

    def test_handles_missing_issue(self):
        """
        Business Rule: Handles payloads without issue gracefully.
        Behavior: Returns model with empty issue_key.
        """
        from api.webhooks.jira.routing import extract_jira_routing

        payload = {}

        routing = extract_jira_routing(payload)

        assert routing.issue_key == ""


class TestSlackRoutingExtractor:
    """Test Slack domain routing extractor."""

    def test_extracts_channel_id_from_event(self):
        """
        Business Rule: Extracts channel ID from Events API payload.
        Behavior: Returns channel_id from payload.event.channel.
        """
        from api.webhooks.slack.routing import extract_slack_routing

        payload = {
            "event": {"channel": "C12345", "ts": "123.456"}
        }

        routing = extract_slack_routing(payload)

        assert isinstance(routing, SlackRoutingMetadata)
        assert routing.channel_id == "C12345"

    def test_extracts_channel_id_from_slash_command(self):
        """
        Business Rule: Extracts channel ID from slash command payload.
        Behavior: Returns channel_id from payload.channel_id.
        """
        from api.webhooks.slack.routing import extract_slack_routing

        payload = {
            "channel_id": "C67890",
            "user_id": "U12345"
        }

        routing = extract_slack_routing(payload)

        assert routing.channel_id == "C67890"

    def test_extracts_thread_ts_from_event(self):
        """
        Business Rule: Extracts thread timestamp from event.
        Behavior: Returns thread_ts from payload.event.thread_ts.
        """
        from api.webhooks.slack.routing import extract_slack_routing

        payload = {
            "event": {"channel": "C12345", "thread_ts": "123.789"}
        }

        routing = extract_slack_routing(payload)

        assert routing.thread_ts == "123.789"

    def test_uses_ts_as_fallback_for_thread_ts(self):
        """
        Business Rule: Uses message ts as fallback for thread.
        Behavior: If no thread_ts, uses event.ts.
        """
        from api.webhooks.slack.routing import extract_slack_routing

        payload = {
            "event": {"channel": "C12345", "ts": "123.456"}
        }

        routing = extract_slack_routing(payload)

        assert routing.thread_ts == "123.456"

    def test_extracts_user_id_from_event(self):
        """
        Business Rule: Extracts user ID from Events API payload.
        Behavior: Returns user_id from payload.event.user.
        """
        from api.webhooks.slack.routing import extract_slack_routing

        payload = {
            "event": {"channel": "C12345", "user": "U99999", "ts": "123.456"}
        }

        routing = extract_slack_routing(payload)

        assert routing.user_id == "U99999"

    def test_extracts_user_id_from_slash_command(self):
        """
        Business Rule: Extracts user ID from slash command payload.
        Behavior: Returns user_id from payload.user_id.
        """
        from api.webhooks.slack.routing import extract_slack_routing

        payload = {
            "channel_id": "C12345",
            "user_id": "U11111"
        }

        routing = extract_slack_routing(payload)

        assert routing.user_id == "U11111"

    def test_extracts_team_id(self):
        """
        Business Rule: Extracts team ID from payload.
        Behavior: Returns team_id from payload.team_id.
        """
        from api.webhooks.slack.routing import extract_slack_routing

        payload = {
            "team_id": "T12345",
            "channel_id": "C12345"
        }

        routing = extract_slack_routing(payload)

        assert routing.team_id == "T12345"

    def test_returns_pydantic_model(self):
        """
        Business Rule: Returns strict Pydantic model.
        Behavior: Return type is SlackRoutingMetadata.
        """
        from api.webhooks.slack.routing import extract_slack_routing

        payload = {"channel_id": "C12345", "team_id": "T12345"}

        routing = extract_slack_routing(payload)

        assert isinstance(routing, SlackRoutingMetadata)

    def test_handles_empty_payload(self):
        """
        Business Rule: Handles empty payloads gracefully.
        Behavior: Returns model with empty channel_id.
        """
        from api.webhooks.slack.routing import extract_slack_routing

        payload = {}

        routing = extract_slack_routing(payload)

        assert routing.channel_id == ""


class TestRoutingMetadataDispatcher:
    """Test the main routing metadata dispatcher."""

    def test_dispatches_to_github_extractor(self):
        """
        Business Rule: Dispatcher routes to GitHub extractor.
        Behavior: webhook_source="github" calls GitHub extractor.
        """
        from core.routing_metadata import extract_routing_metadata_typed

        payload = {
            "repository": {"full_name": "owner/repo"},
            "issue": {"number": 123}
        }

        routing = extract_routing_metadata_typed("github", payload)

        assert isinstance(routing, GitHubRoutingMetadata)
        assert routing.owner == "owner"

    def test_dispatches_to_jira_extractor(self):
        """
        Business Rule: Dispatcher routes to Jira extractor.
        Behavior: webhook_source="jira" calls Jira extractor.
        """
        from core.routing_metadata import extract_routing_metadata_typed

        payload = {"issue": {"key": "PROJ-123"}}

        routing = extract_routing_metadata_typed("jira", payload)

        assert isinstance(routing, JiraRoutingMetadata)
        assert routing.issue_key == "PROJ-123"

    def test_dispatches_to_slack_extractor(self):
        """
        Business Rule: Dispatcher routes to Slack extractor.
        Behavior: webhook_source="slack" calls Slack extractor.
        """
        from core.routing_metadata import extract_routing_metadata_typed

        payload = {"channel_id": "C12345", "team_id": "T12345"}

        routing = extract_routing_metadata_typed("slack", payload)

        assert isinstance(routing, SlackRoutingMetadata)
        assert routing.channel_id == "C12345"

    def test_returns_none_for_unknown_source(self):
        """
        Business Rule: Returns None for unknown webhook source.
        Behavior: Unknown sources return None instead of empty dict.
        """
        from core.routing_metadata import extract_routing_metadata_typed

        routing = extract_routing_metadata_typed("unknown", {})

        assert routing is None
