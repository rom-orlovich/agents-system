"""TDD tests for Slack webhook list value handling."""

import pytest
from unittest.mock import AsyncMock, patch


class TestSlackListHandling:
    
    def test_extract_slack_text_converts_list_to_string(self):
        from api.webhooks.slack.utils import extract_slack_text
        
        assert extract_slack_text(["item1", "item2"]) == "item1 item2"
        assert extract_slack_text(["single"]) == "single"
        assert extract_slack_text([]) == ""
        assert extract_slack_text(None) == ""
        assert extract_slack_text("string") == "string"
        assert extract_slack_text(123) == "123"
    
    def test_extract_slack_text_handles_dict(self):
        from api.webhooks.slack.utils import extract_slack_text
        
        assert extract_slack_text({"text": "hello"}) == "hello"
        assert extract_slack_text({"body": "world"}) == "world"
        assert extract_slack_text({"content": "test"}) == "test"
    
    @pytest.mark.asyncio
    async def test_match_slack_command_handles_list_text(self):
        from api.webhooks.slack.utils import match_slack_command
        from core.webhook_configs import SLACK_WEBHOOK
        from shared.machine_models import WebhookCommand
        
        payload = {
            "event": {
                "type": "message",
                "text": ["@agent", "review", "this"],
                "user": "U123",
                "ts": "1234567890.123456"
            }
        }
        
        with patch("api.webhooks.slack.utils.is_agent_posted_slack_message", new_callable=AsyncMock, return_value=False), \
             patch("api.webhooks.slack.utils.is_agent_own_slack_app", new_callable=AsyncMock, return_value=False), \
             patch("api.webhooks.slack.utils.SLACK_WEBHOOK") as mock_webhook:
            mock_cmd = WebhookCommand(name="review", aliases=[], prompt_template="test", target_agent="brain")
            mock_webhook.commands = [mock_cmd]
            
            result = await match_slack_command(payload, "message")
            assert result is not None
            assert result.name == "review"
    
    @pytest.mark.asyncio
    async def test_match_slack_command_handles_dict_text(self):
        from api.webhooks.slack.utils import match_slack_command
        
        payload = {
            "event": {
                "type": "message",
                "text": {"text": "@agent analyze"},
                "user": "U123",
                "ts": "1234567890.123456"
            }
        }
        
        with patch("api.webhooks.slack.utils.is_agent_posted_slack_message", new_callable=AsyncMock, return_value=False), \
             patch("api.webhooks.slack.utils.is_agent_own_slack_app", new_callable=AsyncMock, return_value=False):
            result = await match_slack_command(payload, "message")
            assert result is not None
            assert result.name == "analyze"
    
    @pytest.mark.asyncio
    async def test_match_slack_command_handles_none_text(self):
        from api.webhooks.slack.utils import match_slack_command
        
        payload = {
            "event": {
                "type": "message",
                "text": None,
                "user": "U123",
                "ts": "1234567890.123456"
            }
        }
        
        with patch("api.webhooks.slack.utils.is_agent_posted_slack_message", new_callable=AsyncMock, return_value=False), \
             patch("api.webhooks.slack.utils.is_agent_own_slack_app", new_callable=AsyncMock, return_value=False):
            result = await match_slack_command(payload, "message")
            assert result is None
    
    def test_slack_webhook_payload_extract_text_handles_list(self):
        from api.webhooks.slack.validation import SlackWebhookPayload
        
        payload = SlackWebhookPayload(
            event={"text": ["@agent", "review", "test"]},
            text=None
        )
        
        text = payload.extract_text()
        assert text == "@agent review test"
    
    def test_slack_webhook_payload_extract_text_handles_dict(self):
        from api.webhooks.slack.validation import SlackWebhookPayload
        
        payload = SlackWebhookPayload(
            event={"text": {"text": "@agent review test"}},
            text=None
        )
        
        text = payload.extract_text()
        assert text == "@agent review test"
