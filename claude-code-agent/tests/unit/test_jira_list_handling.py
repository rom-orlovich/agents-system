"""TDD tests for Jira webhook list value handling."""

import pytest
from unittest.mock import AsyncMock, patch


class TestJiraListHandling:
    """Test that Jira webhook handlers correctly handle list values."""
    
    def test_safe_string_converts_list_to_string(self):
        """
        Business Rule: List values must be converted to strings safely.
        Behavior: _safe_string() converts lists to space-separated strings.
        """
        from api.webhooks.jira.utils import _safe_string
        
        assert _safe_string(["item1", "item2"]) == "item1 item2"
        assert _safe_string(["single"]) == "single"
        assert _safe_string([]) == ""
        assert _safe_string(None) == ""
        assert _safe_string("string") == "string"
        assert _safe_string(123) == "123"
    
    def test_is_assignee_changed_to_ai_handles_list_toString(self):
        """
        Business Rule: is_assignee_changed_to_ai() must handle list values in toString field.
        Behavior: Function works correctly when toString is a list instead of a string.
        """
        from api.webhooks.jira.utils import is_assignee_changed_to_ai
        
        payload = {
            "issue": {"key": "TEST-123"},
            "changelog": {
                "items": [
                    {
                        "field": "assignee",
                        "toString": ["AI Agent", "Team Lead"]
                    }
                ]
            }
        }
        
        with patch('api.webhooks.jira.utils.settings.jira_ai_agent_name', "AI Agent"):
            result = is_assignee_changed_to_ai(payload, "issue_updated")
            assert result is True
    
    def test_is_assignee_changed_to_ai_handles_list_displayName(self):
        """
        Business Rule: is_assignee_changed_to_ai() must handle list values in displayName field.
        Behavior: Function works correctly when displayName is a list instead of a string.
        """
        from api.webhooks.jira.utils import is_assignee_changed_to_ai
        
        payload = {
            "issue": {
                "key": "TEST-456",
                "fields": {
                    "assignee": {
                        "displayName": ["AI Agent", "Bot"]
                    }
                }
            }
        }
        
        with patch('api.webhooks.jira.utils.settings.jira_ai_agent_name', "AI Agent"):
            result = is_assignee_changed_to_ai(payload, "issue_created")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_match_jira_command_handles_list_displayName(self):
        """
        Business Rule: match_jira_command() must handle list values in author displayName.
        Behavior: Function works correctly when displayName is a list instead of a string.
        """
        from api.webhooks.jira.utils import match_jira_command
        
        payload = {
            "comment": {
                "id": "12345",
                "body": "@agent analyze",
                "author": {
                    "accountId": "557058:abc123",
                    "displayName": ["Test User", "Developer"],
                    "accountType": "atlassian"
                }
            },
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Test issue"
                }
            }
        }
        
        with patch('api.webhooks.jira.utils.is_agent_posted_jira_comment', new_callable=AsyncMock, return_value=False), \
             patch('api.webhooks.jira.utils.is_agent_own_jira_account', new_callable=AsyncMock, return_value=False), \
             patch('core.command_matcher.extract_command', return_value=("analyze", "test content")), \
             patch('api.webhooks.jira.utils.JIRA_WEBHOOK') as mock_webhook:
            from shared.machine_models import WebhookCommand
            mock_cmd = WebhookCommand(name="analyze", aliases=[], prompt_template="test", target_agent="brain")
            mock_webhook.commands = [mock_cmd]
            
            result = await match_jira_command(payload, "comment_created")
            
            assert result is not None
            assert result.name == "analyze"
    
    @pytest.mark.asyncio
    async def test_match_jira_command_handles_list_accountType(self):
        """
        Business Rule: match_jira_command() must handle list values in accountType.
        Behavior: Function works correctly when accountType is a list instead of a string.
        """
        from api.webhooks.jira.utils import match_jira_command
        
        payload = {
            "comment": {
                "id": "12345",
                "body": "test comment",
                "author": {
                    "accountId": "557058:abc123",
                    "displayName": "Bot User",
                    "accountType": ["app", "bot"]
                }
            },
            "issue": {
                "key": "PROJ-123"
            }
        }
        
        result = await match_jira_command(payload, "comment_created")
        
        assert result is None
    
    def test_validation_handles_list_displayName(self):
        """
        Business Rule: Jira webhook validation must handle list values in displayName.
        Behavior: Validation works correctly when displayName is a list instead of a string.
        """
        from api.webhooks.jira.validation import validate_jira_webhook
        
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "fields": {
                    "assignee": {
                        "displayName": ["AI Agent", "Team Member"]
                    }
                }
            },
            "changelog": {
                "items": [
                    {
                        "field": "assignee",
                        "toString": ["AI Agent"]
                    }
                ]
            }
        }
        
        result = validate_jira_webhook(payload)
        assert result.is_valid is True
    
    def test_validation_handles_list_toString(self):
        """
        Business Rule: Jira webhook validation must handle list values in toString.
        Behavior: Validation works correctly when toString is a list instead of a string.
        """
        from api.webhooks.jira.validation import validate_jira_webhook
        
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "fields": {
                    "assignee": {
                        "displayName": "AI Agent"
                    }
                }
            },
            "changelog": {
                "items": [
                    {
                        "field": "assignee",
                        "toString": ["AI Agent", "Bot"]
                    }
                ]
            }
        }
        
        result = validate_jira_webhook(payload)
        assert result.is_valid is True
