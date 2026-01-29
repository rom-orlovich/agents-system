"""
Tests for webhook configuration safety and null handling.

These tests verify that the system properly handles cases where webhook
configurations fail to load and are None.
"""
import pytest
from unittest.mock import MagicMock, patch


def test_get_webhook_commands_with_none_config():
    """Test that get_webhook_commands returns empty list for None config."""
    from core.webhook_utils import get_webhook_commands
    
    result = get_webhook_commands(None, "test_webhook")
    assert result == []


def test_get_webhook_commands_with_valid_config():
    """Test that get_webhook_commands returns commands from valid config."""
    from core.webhook_utils import get_webhook_commands
    
    mock_command = MagicMock()
    mock_command.name = "test_command"
    
    mock_config = MagicMock()
    mock_config.commands = [mock_command]
    
    result = get_webhook_commands(mock_config, "test_webhook")
    assert len(result) == 1
    assert result[0].name == "test_command"


def test_get_webhook_commands_with_empty_commands():
    """Test that get_webhook_commands handles empty commands list."""
    from core.webhook_utils import get_webhook_commands
    
    mock_config = MagicMock()
    mock_config.commands = []
    
    result = get_webhook_commands(mock_config, "test_webhook")
    assert result == []


def test_validate_webhook_configs_detects_missing_github():
    """Test that validate_webhook_configs detects missing GitHub config."""
    with patch('core.webhook_configs.GITHUB_WEBHOOK', None):
        with patch('core.webhook_configs.JIRA_WEBHOOK', MagicMock()):
            with patch('core.webhook_configs.SLACK_WEBHOOK', MagicMock()):
                from core.webhook_configs import validate_webhook_configs
                
                with pytest.raises(ValueError) as exc_info:
                    validate_webhook_configs()
                
                error_message = str(exc_info.value)
                assert "Critical webhook configurations missing" in error_message
                assert "github" in error_message


def test_validate_webhook_configs_detects_missing_multiple():
    """Test that validate_webhook_configs detects multiple missing configs."""
    with patch('core.webhook_configs.GITHUB_WEBHOOK', None):
        with patch('core.webhook_configs.JIRA_WEBHOOK', None):
            with patch('core.webhook_configs.SLACK_WEBHOOK', MagicMock()):
                from core.webhook_configs import validate_webhook_configs
                
                with pytest.raises(ValueError) as exc_info:
                    validate_webhook_configs()
                
                error_message = str(exc_info.value)
                assert "Critical webhook configurations missing" in error_message
                assert "github" in error_message
                assert "jira" in error_message


def test_validate_webhook_configs_passes_with_valid_configs():
    """Test that validate_webhook_configs passes with all valid configs."""
    mock_config = MagicMock()
    mock_config.name = "test"
    mock_config.commands = []
    
    with patch('core.webhook_configs.GITHUB_WEBHOOK', mock_config):
        with patch('core.webhook_configs.JIRA_WEBHOOK', mock_config):
            with patch('core.webhook_configs.SLACK_WEBHOOK', mock_config):
                with patch('core.webhook_configs.validate_all_configs', return_value=True):
                    from core.webhook_configs import validate_webhook_configs
                    # Should not raise
                    validate_webhook_configs()
