"""Tests for task routing business logic.

Tests routing of tasks to specialized agents based on source.
"""

ROUTING_TABLE: dict[str, dict[str, str]] = {
    "github": {
        "issues": "github-issue-handler",
        "issue_comment": "github-issue-handler",
        "pull_request": "github-pr-review",
        "pull_request_review_comment": "github-pr-review",
    },
    "jira": {
        "jira:issue_created": "jira-code-plan",
        "jira:issue_updated": "jira-code-plan",
        "comment_created": "jira-code-plan",
    },
    "slack": {
        "app_mention": "slack-inquiry",
        "message": "slack-inquiry",
    },
    "sentry": {
        "issue.created": "sentry-error-handler",
        "issue.regression": "sentry-error-handler",
    },
    "dashboard": {
        "discovery": "planning",
        "implementation": "executor",
        "question": "brain",
    },
}


def route_task(source: str, event_type: str) -> str | None:
    """Route a task to the appropriate agent based on source and event type."""
    source_routes = ROUTING_TABLE.get(source, {})
    return source_routes.get(event_type)


class TestGitHubRouting:
    """Tests for GitHub event routing."""

    def test_github_issue_routes_to_issue_handler(self):
        """Business requirement: Issue handling specialized."""
        agent = route_task("github", "issues")
        assert agent == "github-issue-handler"

    def test_github_issue_comment_routes_to_issue_handler(self):
        """Business requirement: Issue comments go to issue handler."""
        agent = route_task("github", "issue_comment")
        assert agent == "github-issue-handler"

    def test_github_pr_routes_to_pr_review(self):
        """Business requirement: PR review specialized."""
        agent = route_task("github", "pull_request")
        assert agent == "github-pr-review"

    def test_github_pr_review_comment_routes_to_pr_review(self):
        """Business requirement: PR comments go to PR reviewer."""
        agent = route_task("github", "pull_request_review_comment")
        assert agent == "github-pr-review"


class TestJiraRouting:
    """Tests for Jira event routing."""

    def test_jira_ticket_routes_to_code_plan(self):
        """Business requirement: Jira integration."""
        agent = route_task("jira", "jira:issue_created")
        assert agent == "jira-code-plan"

    def test_jira_updated_routes_to_code_plan(self):
        """Business requirement: Updated Jira tickets go to code plan."""
        agent = route_task("jira", "jira:issue_updated")
        assert agent == "jira-code-plan"

    def test_jira_comment_routes_to_code_plan(self):
        """Business requirement: Jira comments go to code plan."""
        agent = route_task("jira", "comment_created")
        assert agent == "jira-code-plan"


class TestSlackRouting:
    """Tests for Slack event routing."""

    def test_slack_message_routes_to_inquiry(self):
        """Business requirement: Slack Q&A."""
        agent = route_task("slack", "app_mention")
        assert agent == "slack-inquiry"

    def test_slack_dm_routes_to_inquiry(self):
        """Business requirement: Direct messages go to inquiry."""
        agent = route_task("slack", "message")
        assert agent == "slack-inquiry"


class TestSentryRouting:
    """Tests for Sentry event routing."""

    def test_sentry_alert_routes_to_error_handler(self):
        """Business requirement: Error triage."""
        agent = route_task("sentry", "issue.created")
        assert agent == "sentry-error-handler"

    def test_sentry_regression_routes_to_error_handler(self):
        """Business requirement: Regressions go to error handler."""
        agent = route_task("sentry", "issue.regression")
        assert agent == "sentry-error-handler"


class TestDashboardRouting:
    """Tests for dashboard-initiated task routing."""

    def test_discovery_task_routes_to_planning(self):
        """Business requirement: Code discovery."""
        agent = route_task("dashboard", "discovery")
        assert agent == "planning"

    def test_implementation_task_routes_to_executor(self):
        """Business requirement: Implementation requests."""
        agent = route_task("dashboard", "implementation")
        assert agent == "executor"

    def test_question_task_routes_to_brain(self):
        """Business requirement: Questions go to brain agent."""
        agent = route_task("dashboard", "question")
        assert agent == "brain"


class TestUnknownRoutes:
    """Tests for unknown routing scenarios."""

    def test_unknown_source_returns_none(self):
        """Unknown sources should return None."""
        agent = route_task("unknown", "some_event")
        assert agent is None

    def test_unknown_event_type_returns_none(self):
        """Unknown event types should return None."""
        agent = route_task("github", "unknown_event")
        assert agent is None


class TestRoutingTable:
    """Tests for routing table completeness."""

    def test_all_sources_have_routes(self):
        """All expected sources are in routing table."""
        expected_sources = ["github", "jira", "slack", "sentry", "dashboard"]
        for source in expected_sources:
            assert source in ROUTING_TABLE

    def test_github_has_all_event_types(self):
        """GitHub has all expected event type routes."""
        expected_events = [
            "issues",
            "issue_comment",
            "pull_request",
            "pull_request_review_comment",
        ]
        for event in expected_events:
            assert event in ROUTING_TABLE["github"]

    def test_jira_has_all_event_types(self):
        """Jira has all expected event type routes."""
        expected_events = [
            "jira:issue_created",
            "jira:issue_updated",
            "comment_created",
        ]
        for event in expected_events:
            assert event in ROUTING_TABLE["jira"]
