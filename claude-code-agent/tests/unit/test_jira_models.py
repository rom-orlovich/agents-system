"""
Unit tests for Jira Pydantic models.
"""

import pytest
from pydantic import ValidationError


class TestJiraTaskCompletionPayload:
    """Tests for JiraTaskCompletionPayload model."""
    
    def test_validates_with_issue_key(self):
        """Test that payload validates with issue key."""
        from api.webhooks.jira.models import JiraTaskCompletionPayload
        
        payload = JiraTaskCompletionPayload(
            issue={"key": "KAN-5", "fields": {"summary": "Test"}},
            comment={"body": "Test comment"},
            user_content="analyze error"
        )
        
        assert payload.issue["key"] == "KAN-5"
        assert payload.comment["body"] == "Test comment"
        assert payload.user_content == "analyze error"
    
    def test_allows_empty_optional_fields(self):
        """Test that optional fields can be empty."""
        from api.webhooks.jira.models import JiraTaskCompletionPayload
        
        payload = JiraTaskCompletionPayload(
            issue={"key": "PROJ-123"}
        )
        
        assert payload.issue["key"] == "PROJ-123"
        assert payload.comment is None
        assert payload.user_content is None
    
    def test_extracts_ticket_key(self):
        """Test extraction of ticket key from issue."""
        from api.webhooks.jira.models import JiraTaskCompletionPayload
        
        payload = JiraTaskCompletionPayload(
            issue={"key": "TICKET-456", "fields": {"summary": "Test"}}
        )
        
        assert payload.get_ticket_key() == "TICKET-456"
    
    def test_extracts_user_request_from_comment(self):
        """Test extraction of user request from comment body."""
        from api.webhooks.jira.models import JiraTaskCompletionPayload
        
        payload = JiraTaskCompletionPayload(
            issue={"key": "KAN-5"},
            comment={"body": "@agent analyze Sentry error"}
        )
        
        user_request = payload.get_user_request()
        assert "Sentry error" in user_request or "analyze Sentry error" in user_request or "@agent analyze Sentry error" in user_request
    
    def test_extracts_user_request_from_adf_comment(self):
        """Test extraction of user request from ADF format comment body."""
        from api.webhooks.jira.models import JiraTaskCompletionPayload
        
        adf_body = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "@agent analyze Sentry error"
                        }
                    ]
                }
            ]
        }
        
        payload = JiraTaskCompletionPayload(
            issue={"key": "KAN-5"},
            comment={"body": adf_body}
        )
        
        user_request = payload.get_user_request()
        assert "Sentry error" in user_request or "analyze Sentry error" in user_request or "@agent analyze Sentry error" in user_request
    
    def test_extracts_user_request_from_list_adf_comment(self):
        """Test extraction of user request from list-formatted ADF comment body."""
        from api.webhooks.jira.models import JiraTaskCompletionPayload
        
        adf_body = [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "@agent analyze error"
                    }
                ]
            }
        ]
        
        payload = JiraTaskCompletionPayload(
            issue={"key": "KAN-5"},
            comment={"body": adf_body}
        )
        
        user_request = payload.get_user_request()
        assert user_request == "error"
    
    def test_extracts_user_request_from_user_content(self):
        """Test extraction of user request from _user_content."""
        from api.webhooks.jira.models import JiraTaskCompletionPayload
        
        payload = JiraTaskCompletionPayload(
            issue={"key": "KAN-5"},
            user_content="analyze Sentry error"
        )
        
        assert payload.get_user_request() == "analyze Sentry error"
    
    def test_extracts_user_request_from_issue_description(self):
        """Test extraction of user request from issue description."""
        from api.webhooks.jira.models import JiraTaskCompletionPayload
        
        payload = JiraTaskCompletionPayload(
            issue={
                "key": "PROJ-123",
                "fields": {
                    "description": "Please analyze this issue",
                    "summary": "Test issue"
                }
            }
        )
        
        user_request = payload.get_user_request()
        assert "analyze" in user_request.lower() or "test issue" in user_request.lower()


class TestSlackNotificationRequest:
    """Tests for SlackNotificationRequest model."""
    
    def test_validates_required_fields(self):
        """Test that required fields are validated."""
        from api.webhooks.jira.models import SlackNotificationRequest
        
        request = SlackNotificationRequest(
            task_id="task-123",
            webhook_source="jira",
            command="analyze",
            success=True
        )
        
        assert request.task_id == "task-123"
        assert request.webhook_source == "jira"
        assert request.command == "analyze"
        assert request.success is True
    
    def test_allows_optional_fields(self):
        """Test that optional fields can be provided."""
        from api.webhooks.jira.models import SlackNotificationRequest
        
        request = SlackNotificationRequest(
            task_id="task-123",
            webhook_source="jira",
            command="analyze",
            success=True,
            result="Task completed",
            error=None,
            pr_url="https://github.com/test/repo/pull/123",
            cost_usd=0.05,
            user_request="analyze error",
            ticket_key="KAN-5"
        )
        
        assert request.result == "Task completed"
        assert request.pr_url == "https://github.com/test/repo/pull/123"
        assert request.cost_usd == 0.05
        assert request.user_request == "analyze error"
        assert request.ticket_key == "KAN-5"
    
    def test_validates_cost_non_negative(self):
        """Test that cost must be non-negative."""
        from api.webhooks.jira.models import SlackNotificationRequest
        
        with pytest.raises(ValidationError):
            SlackNotificationRequest(
                task_id="task-123",
                webhook_source="jira",
                command="analyze",
                success=True,
                cost_usd=-1.0
            )


class TestJiraTaskCommentRequest:
    """Tests for JiraTaskCommentRequest model."""
    
    def test_validates_with_issue_key(self):
        """Test that request validates with issue key."""
        from api.webhooks.jira.models import JiraTaskCommentRequest
        
        request = JiraTaskCommentRequest(
            issue={"key": "KAN-5"},
            message="Task completed",
            success=True
        )
        
        assert request.get_issue_key() == "KAN-5"
        assert request.message == "Task completed"
        assert request.success is True
    
    def test_allows_optional_pr_url(self):
        """Test that PR URL is optional."""
        from api.webhooks.jira.models import JiraTaskCommentRequest
        
        request = JiraTaskCommentRequest(
            issue={"key": "KAN-5"},
            message="Task completed",
            success=True,
            pr_url="https://github.com/test/repo/pull/123"
        )
        
        assert request.pr_url == "https://github.com/test/repo/pull/123"
    
    def test_validates_cost_non_negative(self):
        """Test that cost must be non-negative."""
        from api.webhooks.jira.models import JiraTaskCommentRequest
        
        with pytest.raises(ValidationError):
            JiraTaskCommentRequest(
                issue={"key": "KAN-5"},
                message="Task completed",
                success=True,
                cost_usd=-1.0
            )


class TestTaskSummary:
    """Tests for TaskSummary model."""
    
    def test_validates_with_summary(self):
        """Test that summary validates with summary text."""
        from api.webhooks.jira.models import TaskSummary
        
        summary = TaskSummary(
            summary="Analysis complete",
            classification="SIMPLE"
        )
        
        assert summary.summary == "Analysis complete"
        assert summary.classification == "SIMPLE"
    
    def test_allows_optional_fields(self):
        """Test that optional fields can be provided."""
        from api.webhooks.jira.models import TaskSummary
        
        summary = TaskSummary(
            summary="Analysis complete",
            classification="SIMPLE",
            what_was_done="Analyzed error",
            key_insights="No production bug found"
        )
        
        assert summary.what_was_done == "Analyzed error"
        assert summary.key_insights == "No production bug found"
    
    def test_defaults_classification(self):
        """Test that classification defaults to SIMPLE."""
        from api.webhooks.jira.models import TaskSummary
        
        summary = TaskSummary(summary="Test")
        
        assert summary.classification == "SIMPLE"


class TestRoutingMetadata:
    """Tests for RoutingMetadata model."""
    
    def test_validates_with_repo_and_pr(self):
        """Test that routing validates with repo and PR number."""
        from api.webhooks.jira.models import RoutingMetadata
        
        routing = RoutingMetadata(
            repo="owner/repo",
            pr_number=123
        )
        
        assert routing.repo == "owner/repo"
        assert routing.pr_number == 123
    
    def test_allows_empty_routing(self):
        """Test that routing can be empty."""
        from api.webhooks.jira.models import RoutingMetadata
        
        routing = RoutingMetadata()
        
        assert routing.repo is None
        assert routing.pr_number is None
    
    def test_validates_pr_number_positive(self):
        """Test that PR number must be positive."""
        from api.webhooks.jira.models import RoutingMetadata
        
        with pytest.raises(ValidationError):
            RoutingMetadata(
                repo="owner/repo",
                pr_number=-1
            )


class TestPRRouting:
    """Tests for PRRouting model."""
    
    def test_validates_with_repo_and_pr(self):
        """Test that PR routing validates with repo and PR number."""
        from api.webhooks.jira.models import PRRouting
        
        routing = PRRouting(
            repo="owner/repo",
            pr_number=123
        )
        
        assert routing.repo == "owner/repo"
        assert routing.pr_number == 123
    
    def test_validates_pr_number_positive(self):
        """Test that PR number must be positive."""
        from api.webhooks.jira.models import PRRouting
        
        with pytest.raises(ValidationError):
            PRRouting(
                repo="owner/repo",
                pr_number=0
            )
