"""TDD tests for command matcher list handling edge cases."""

import pytest


class TestCommandMatcherListHandling:
    
    def test_is_bot_comment_handles_list_sender_login(self):
        from core.command_matcher import is_bot_comment
        
        result = is_bot_comment(["github-actions", "[bot]"], "Bot")
        assert result is True
    
    def test_is_bot_comment_handles_list_sender_type(self):
        from core.command_matcher import is_bot_comment
        
        result = is_bot_comment("test-bot", ["Bot", "App"])
        assert result is True
    
    def test_is_bot_comment_handles_dict_sender_login(self):
        from core.command_matcher import is_bot_comment
        
        result = is_bot_comment({"name": "bot-user"}, "User")
        assert result is False
    
    def test_is_bot_comment_handles_none_sender_login(self):
        from core.command_matcher import is_bot_comment
        
        result = is_bot_comment(None, "User")
        assert result is False
    
    def test_is_bot_comment_handles_none_sender_type(self):
        from core.command_matcher import is_bot_comment
        
        result = is_bot_comment("test-user", None)
        assert result is False
