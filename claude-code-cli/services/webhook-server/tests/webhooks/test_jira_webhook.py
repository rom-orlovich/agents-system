"""
Tests for JiraWebhookHandler.
"""

import pytest
from webhooks.jira_webhook import JiraWebhookHandler


@pytest.fixture
def handler():
    """Create JiraWebhookHandler instance."""
    return JiraWebhookHandler()


def test_metadata(handler):
    """Test that metadata is correctly defined."""
    metadata = handler.metadata

    assert metadata.name == "jira"
    assert metadata.endpoint == "/webhooks/jira"
    assert metadata.enabled is True
    assert "Jira" in metadata.description


@pytest.mark.asyncio
async def test_parse_payload_with_ai_fix_label(handler):
    """Test parsing Jira payload with AI-Fix label."""
    payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "TEST-123",
            "fields": {
                "summary": "Test issue",
                "description": "Test description",
                "labels": ["AI-Fix", "bug"],
                "status": {"name": "Open"}
            }
        }
    }

    parsed = await handler.parse_payload(payload)

    assert parsed is not None
    assert parsed["issue_key"] == "TEST-123"
    assert parsed["summary"] == "Test issue"
    assert parsed["labels"] == ["AI-Fix", "bug"]
    assert parsed["webhook_event"] == "jira:issue_created"


@pytest.mark.asyncio
async def test_parse_payload_with_sentry_issue(handler):
    """Test parsing Jira payload with Sentry issue."""
    payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "TEST-456",
            "fields": {
                "summary": "Sentry error",
                "description": "Sentry Issue: [JAVASCRIPT-REACT-1](https://sentry.io/...)",
                "labels": [],
                "status": {"name": "Open"}
            }
        }
    }

    parsed = await handler.parse_payload(payload)

    assert parsed is not None
    assert parsed["sentry_issue_id"] == "JAVASCRIPT-REACT-1"


@pytest.mark.asyncio
async def test_should_process_with_ai_fix_label(handler):
    """Test that issues with AI-Fix label should be processed."""
    parsed_data = {
        "webhook_event": "jira:issue_created",
        "labels": ["AI-Fix", "bug"],
        "issue_key": "TEST-123",
        "sentry_issue_id": None,
        "summary": "Test issue",
        "changelog": {}
    }

    should_process = await handler.should_process(parsed_data)

    assert should_process is True


@pytest.mark.asyncio
async def test_should_process_with_sentry_issue(handler):
    """Test that Sentry-created issues should be processed."""
    parsed_data = {
        "webhook_event": "jira:issue_created",
        "labels": [],
        "issue_key": "TEST-456",
        "sentry_issue_id": "JAVASCRIPT-REACT-1",
        "summary": "Sentry error",
        "changelog": {}
    }

    should_process = await handler.should_process(parsed_data)

    assert should_process is True


@pytest.mark.asyncio
async def test_should_process_with_sentry_in_summary(handler):
    """Test that issues with 'sentry' in summary should be processed."""
    parsed_data = {
        "webhook_event": "jira:issue_created",
        "labels": [],
        "issue_key": "TEST-789",
        "sentry_issue_id": None,
        "summary": "Sentry: JavaScript error",
        "changelog": {}
    }

    should_process = await handler.should_process(parsed_data)

    assert should_process is True


@pytest.mark.asyncio
async def test_should_not_process_regular_issue(handler):
    """Test that regular issues should not be processed."""
    parsed_data = {
        "webhook_event": "jira:issue_created",
        "labels": ["bug"],
        "issue_key": "TEST-999",
        "sentry_issue_id": None,
        "summary": "Regular bug",
        "changelog": {}
    }

    should_process = await handler.should_process(parsed_data)

    assert should_process is False


@pytest.mark.asyncio
async def test_should_process_approval_transition(handler):
    """Test that approval transitions should be processed."""
    parsed_data = {
        "webhook_event": "jira:issue_updated",
        "labels": [],
        "issue_key": "TEST-111",
        "sentry_issue_id": None,
        "summary": "Test issue",
        "changelog": {
            "items": [
                {
                    "field": "status",
                    "fromString": "Pending",
                    "toString": "Approved"
                }
            ]
        }
    }

    should_process = await handler.should_process(parsed_data)

    assert should_process is True


def test_extract_sentry_issue_id_markdown_format(handler):
    """Test extracting Sentry issue ID from markdown link."""
    description = "Error occurred. Sentry Issue: [JAVASCRIPT-REACT-1](https://sentry.io/...)"

    issue_id = handler._extract_sentry_issue_id(description)

    assert issue_id == "JAVASCRIPT-REACT-1"


def test_extract_sentry_issue_id_plain_format(handler):
    """Test extracting Sentry issue ID from plain text."""
    description = "Error occurred. Sentry Issue: JAVASCRIPT-REACT-2"

    issue_id = handler._extract_sentry_issue_id(description)

    assert issue_id == "JAVASCRIPT-REACT-2"


def test_extract_sentry_issue_id_anywhere(handler):
    """Test extracting Sentry issue ID from anywhere in text."""
    description = "Some error with JAVASCRIPT-REACT-3 in production"

    issue_id = handler._extract_sentry_issue_id(description)

    assert issue_id == "JAVASCRIPT-REACT-3"


def test_extract_sentry_issue_id_none(handler):
    """Test that None is returned when no issue ID found."""
    description = "Regular issue with no Sentry ID"

    issue_id = handler._extract_sentry_issue_id(description)

    assert issue_id is None


def test_extract_repository_from_github_url(handler):
    """Test extracting repository from GitHub URL."""
    description = "Repository: https://github.com/owner/repo"

    repo = handler._extract_repository(description)

    assert repo == "owner/repo"


def test_extract_repository_from_label(handler):
    """Test extracting repository from Repository: label."""
    description = "Repository: owner/repo\nSome other text"

    repo = handler._extract_repository(description)

    assert repo == "owner/repo"


def test_extract_repository_none(handler):
    """Test that None is returned when no repository found."""
    description = "Issue with no repository information"

    repo = handler._extract_repository(description)

    assert repo is None
