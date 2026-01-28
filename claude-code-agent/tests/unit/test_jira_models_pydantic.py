import pytest
from pydantic import ValidationError, TypeAdapter
from api.webhooks.jira.models import (
    JiraUser,
    JiraProject,
    JiraIssueType,
    JiraStatus,
    JiraIssueFields,
    JiraIssue,
    JiraComment,
    JiraChangelogItem,
    JiraChangelog,
    JiraWebhookPayload,
    JiraIssueEventPayload,
    JiraCommentEventPayload,
)

JiraPayloadAdapter = TypeAdapter(JiraWebhookPayload)


class TestJiraUser:
    def test_valid_user(self):
        user_data = {
            "self": "https://jira.example.com/rest/api/2/user?accountId=123",
            "accountId": "123",
            "emailAddress": "user@example.com",
            "displayName": "Test User",
            "active": True,
        }
        user = JiraUser(**user_data)
        assert user.accountId == "123"
        assert user.displayName == "Test User"
        assert user.emailAddress == "user@example.com"

    def test_user_missing_required_fields(self):
        user_data = {"accountId": "123"}
        with pytest.raises(ValidationError) as exc_info:
            JiraUser(**user_data)
        assert "displayName" in str(exc_info.value)


class TestJiraProject:
    def test_valid_project(self):
        project_data = {
            "self": "https://jira.example.com/rest/api/2/project/10000",
            "id": "10000",
            "key": "TEST",
            "name": "Test Project",
        }
        project = JiraProject(**project_data)
        assert project.key == "TEST"
        assert project.name == "Test Project"

    def test_project_missing_key(self):
        project_data = {
            "self": "https://jira.example.com/rest/api/2/project/10000",
            "id": "10000",
            "name": "Test Project",
        }
        with pytest.raises(ValidationError) as exc_info:
            JiraProject(**project_data)
        assert "key" in str(exc_info.value)


class TestJiraIssue:
    def test_valid_issue(self):
        issue_data = {
            "id": "10001",
            "key": "TEST-123",
            "self": "https://jira.example.com/rest/api/2/issue/10001",
            "fields": {
                "summary": "Test Issue",
                "description": "This is a test issue",
                "status": {"id": "1", "name": "Open"},
                "issuetype": {"id": "10001", "name": "Task"},
                "project": {
                    "id": "10000",
                    "key": "TEST",
                    "name": "Test Project",
                    "self": "https://jira.example.com/rest/api/2/project/10000",
                },
            },
        }
        issue = JiraIssue(**issue_data)
        assert issue.key == "TEST-123"
        assert issue.fields.summary == "Test Issue"
        assert issue.fields.description == "This is a test issue"

    def test_issue_without_description(self):
        issue_data = {
            "id": "10001",
            "key": "TEST-123",
            "self": "https://jira.example.com/rest/api/2/issue/10001",
            "fields": {
                "summary": "Test Issue",
                "status": {"id": "1", "name": "Open"},
                "issuetype": {"id": "10001", "name": "Task"},
                "project": {
                    "id": "10000",
                    "key": "TEST",
                    "name": "Test Project",
                    "self": "https://jira.example.com/rest/api/2/project/10000",
                },
            },
        }
        issue = JiraIssue(**issue_data)
        assert issue.fields.description is None


class TestJiraComment:
    def test_valid_comment(self):
        comment_data = {
            "self": "https://jira.example.com/rest/api/2/issue/10001/comment/10200",
            "id": "10200",
            "author": {
                "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                "accountId": "123",
                "displayName": "Test User",
                "active": True,
            },
            "body": "@agent analyze this issue",
            "created": "2024-01-01T00:00:00.000+0000",
        }
        comment = JiraComment(**comment_data)
        assert comment.id == "10200"
        assert comment.body == "@agent analyze this issue"
        assert comment.author.displayName == "Test User"

    def test_comment_missing_body(self):
        comment_data = {
            "self": "https://jira.example.com/rest/api/2/issue/10001/comment/10200",
            "id": "10200",
            "author": {
                "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                "accountId": "123",
                "displayName": "Test User",
                "active": True,
            },
            "created": "2024-01-01T00:00:00.000+0000",
        }
        with pytest.raises(ValidationError) as exc_info:
            JiraComment(**comment_data)
        assert "body" in str(exc_info.value)


class TestJiraIssueEventPayload:
    def test_valid_issue_created_event(self):
        payload_data = {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "id": "10001",
                "key": "TEST-123",
                "self": "https://jira.example.com/rest/api/2/issue/10001",
                "fields": {
                    "summary": "New Issue",
                    "description": "@agent analyze this",
                    "status": {"id": "1", "name": "Open"},
                    "issuetype": {"id": "10001", "name": "Task"},
                    "project": {
                        "id": "10000",
                        "key": "TEST",
                        "name": "Test Project",
                        "self": "https://jira.example.com/rest/api/2/project/10000",
                    },
                },
            },
            "user": {
                "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                "accountId": "123",
                "displayName": "Test User",
                "active": True,
            },
        }
        payload = JiraIssueEventPayload(**payload_data)
        assert payload.webhookEvent == "jira:issue_created"
        assert payload.issue.key == "TEST-123"
        assert payload.user.displayName == "Test User"

    def test_issue_event_text_extraction(self):
        payload_data = {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "id": "10001",
                "key": "TEST-123",
                "self": "https://jira.example.com/rest/api/2/issue/10001",
                "fields": {
                    "summary": "Issue Summary",
                    "description": "Issue description text",
                    "status": {"id": "1", "name": "Open"},
                    "issuetype": {"id": "10001", "name": "Task"},
                    "project": {
                        "id": "10000",
                        "key": "TEST",
                        "name": "Test Project",
                        "self": "https://jira.example.com/rest/api/2/project/10000",
                    },
                },
            },
            "user": {
                "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                "accountId": "123",
                "displayName": "Test User",
                "active": True,
            },
        }
        payload = JiraIssueEventPayload(**payload_data)
        text = payload.extract_text()
        assert "Issue Summary" in text
        assert "Issue description text" in text


class TestJiraCommentEventPayload:
    def test_valid_comment_created_event(self):
        payload_data = {
            "webhookEvent": "comment_created",
            "comment": {
                "self": "https://jira.example.com/rest/api/2/issue/10001/comment/10200",
                "id": "10200",
                "author": {
                    "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                    "accountId": "123",
                    "displayName": "Test User",
                    "active": True,
                },
                "body": "@agent fix this issue",
                "created": "2024-01-01T00:00:00.000+0000",
            },
            "issue": {
                "id": "10001",
                "key": "TEST-123",
                "self": "https://jira.example.com/rest/api/2/issue/10001",
                "fields": {
                    "summary": "Test Issue",
                    "status": {"id": "1", "name": "Open"},
                    "issuetype": {"id": "10001", "name": "Task"},
                    "project": {
                        "id": "10000",
                        "key": "TEST",
                        "name": "Test Project",
                        "self": "https://jira.example.com/rest/api/2/project/10000",
                    },
                },
            },
            "user": {
                "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                "accountId": "123",
                "displayName": "Test User",
                "active": True,
            },
        }
        payload = JiraCommentEventPayload(**payload_data)
        assert payload.webhookEvent == "comment_created"
        assert payload.comment.body == "@agent fix this issue"
        assert payload.issue.key == "TEST-123"

    def test_comment_event_text_extraction(self):
        payload_data = {
            "webhookEvent": "comment_created",
            "comment": {
                "self": "https://jira.example.com/rest/api/2/issue/10001/comment/10200",
                "id": "10200",
                "author": {
                    "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                    "accountId": "123",
                    "displayName": "Test User",
                    "active": True,
                },
                "body": "Comment body text",
                "created": "2024-01-01T00:00:00.000+0000",
            },
            "issue": {
                "id": "10001",
                "key": "TEST-123",
                "self": "https://jira.example.com/rest/api/2/issue/10001",
                "fields": {
                    "summary": "Test Issue",
                    "status": {"id": "1", "name": "Open"},
                    "issuetype": {"id": "10001", "name": "Task"},
                    "project": {
                        "id": "10000",
                        "key": "TEST",
                        "name": "Test Project",
                        "self": "https://jira.example.com/rest/api/2/project/10000",
                    },
                },
            },
            "user": {
                "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                "accountId": "123",
                "displayName": "Test User",
                "active": True,
            },
        }
        payload = JiraCommentEventPayload(**payload_data)
        text = payload.extract_text()
        assert text == "Comment body text"


class TestJiraWebhookPayload:
    def test_discriminated_union_issue_event(self):
        payload_data = {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "id": "10001",
                "key": "TEST-123",
                "self": "https://jira.example.com/rest/api/2/issue/10001",
                "fields": {
                    "summary": "New Issue",
                    "status": {"id": "1", "name": "Open"},
                    "issuetype": {"id": "10001", "name": "Task"},
                    "project": {
                        "id": "10000",
                        "key": "TEST",
                        "name": "Test Project",
                        "self": "https://jira.example.com/rest/api/2/project/10000",
                    },
                },
            },
            "user": {
                "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                "accountId": "123",
                "displayName": "Test User",
                "active": True,
            },
        }
        payload = JiraPayloadAdapter.validate_python(payload_data)
        assert isinstance(payload, JiraIssueEventPayload)
        assert payload.issue.key == "TEST-123"

    def test_discriminated_union_comment_event(self):
        payload_data = {
            "webhookEvent": "comment_created",
            "comment": {
                "self": "https://jira.example.com/rest/api/2/issue/10001/comment/10200",
                "id": "10200",
                "author": {
                    "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                    "accountId": "123",
                    "displayName": "Test User",
                    "active": True,
                },
                "body": "@agent fix this",
                "created": "2024-01-01T00:00:00.000+0000",
            },
            "issue": {
                "id": "10001",
                "key": "TEST-123",
                "self": "https://jira.example.com/rest/api/2/issue/10001",
                "fields": {
                    "summary": "Test Issue",
                    "status": {"id": "1", "name": "Open"},
                    "issuetype": {"id": "10001", "name": "Task"},
                    "project": {
                        "id": "10000",
                        "key": "TEST",
                        "name": "Test Project",
                        "self": "https://jira.example.com/rest/api/2/project/10000",
                    },
                },
            },
            "user": {
                "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                "accountId": "123",
                "displayName": "Test User",
                "active": True,
            },
        }
        payload = JiraPayloadAdapter.validate_python(payload_data)
        assert isinstance(payload, JiraCommentEventPayload)
        assert payload.comment.body == "@agent fix this"

    def test_text_extraction_priority_comment_over_issue(self):
        payload_data = {
            "webhookEvent": "comment_created",
            "comment": {
                "self": "https://jira.example.com/rest/api/2/issue/10001/comment/10200",
                "id": "10200",
                "author": {
                    "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                    "accountId": "123",
                    "displayName": "Test User",
                    "active": True,
                },
                "body": "Comment text",
                "created": "2024-01-01T00:00:00.000+0000",
            },
            "issue": {
                "id": "10001",
                "key": "TEST-123",
                "self": "https://jira.example.com/rest/api/2/issue/10001",
                "fields": {
                    "summary": "Issue Summary",
                    "description": "Issue description",
                    "status": {"id": "1", "name": "Open"},
                    "issuetype": {"id": "10001", "name": "Task"},
                    "project": {
                        "id": "10000",
                        "key": "TEST",
                        "name": "Test Project",
                        "self": "https://jira.example.com/rest/api/2/project/10000",
                    },
                },
            },
            "user": {
                "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                "accountId": "123",
                "displayName": "Test User",
                "active": True,
            },
        }
        payload = JiraPayloadAdapter.validate_python(payload_data)
        text = payload.extract_text()
        assert text == "Comment text"

    def test_validation_error_invalid_webhook_event(self):
        payload_data = {
            "webhookEvent": "invalid_event",
            "issue": {
                "id": "10001",
                "key": "TEST-123",
                "self": "https://jira.example.com/rest/api/2/issue/10001",
                "fields": {
                    "summary": "New Issue",
                    "status": {"id": "1", "name": "Open"},
                    "issuetype": {"id": "10001", "name": "Task"},
                    "project": {
                        "id": "10000",
                        "key": "TEST",
                        "name": "Test Project",
                        "self": "https://jira.example.com/rest/api/2/project/10000",
                    },
                },
            },
            "user": {
                "self": "https://jira.example.com/rest/api/2/user?accountId=123",
                "accountId": "123",
                "displayName": "Test User",
                "active": True,
            },
        }
        with pytest.raises(ValidationError):
            JiraPayloadAdapter.validate_python(payload_data)
