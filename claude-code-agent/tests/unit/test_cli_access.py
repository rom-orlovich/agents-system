"""Unit tests for CLI access testing function."""

import pytest
from unittest.mock import patch, MagicMock
import subprocess

# Import will be available after we create the module
# from core.cli_access import test_cli_access
async def test_cli_access_success_returns_true():
    """test_cli_access() returns True when CLI test succeeds."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        from core.cli_access import test_cli_access
        result = await test_cli_access()
        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["claude", "-p", "--output-format", "json", "--dangerously-skip-permissions", "--", "test"]
async def test_cli_access_failure_returns_false():
    """test_cli_access() returns False when CLI test fails."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        from core.cli_access import test_cli_access
        result = await test_cli_access()
        assert result is False
async def test_cli_access_timeout_returns_false():
    """test_cli_access() returns False on timeout."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 10)
        from core.cli_access import test_cli_access
        result = await test_cli_access()
        assert result is False
async def test_cli_access_file_not_found_returns_false():
    """test_cli_access() returns False when CLI not found."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError()
        from core.cli_access import test_cli_access
        result = await test_cli_access()
        assert result is False
async def test_cli_access_exception_returns_false():
    """test_cli_access() returns False on any exception."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = Exception("Unexpected error")
        from core.cli_access import test_cli_access
        result = await test_cli_access()
        assert result is False


async def test_cli_access_logs_stderr_on_failure():
    """test_cli_access() logs stderr when CLI returns non-zero exit code."""
    from core.cli_access import test_cli_access
    from unittest.mock import MagicMock
    
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Rate limit exceeded"
    mock_result.stdout = ""
    
    with patch('subprocess.run', return_value=mock_result):
        with patch('core.cli_access.logger') as mock_logger:
            result = await test_cli_access()
            
            assert result is False
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args.kwargs["returncode"] == 1
            assert call_args.kwargs["error"] == "Rate limit exceeded"


async def test_cli_access_handles_empty_stderr():
    """test_cli_access() handles empty stderr gracefully."""
    from core.cli_access import test_cli_access
    from unittest.mock import MagicMock
    
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = None
    mock_result.stdout = None
    
    with patch('subprocess.run', return_value=mock_result):
        with patch('core.cli_access.logger') as mock_logger:
            result = await test_cli_access()
            
            assert result is False
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args.kwargs["error"] == "Unknown error"


async def test_cli_access_handles_rate_limit_error():
    """test_cli_access() returns False and logs rate limit errors."""
    from core.cli_access import test_cli_access
    from unittest.mock import MagicMock
    
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error: You're out of extra usage · resets 9pm (UTC)"
    
    with patch('subprocess.run', return_value=mock_result):
        result = await test_cli_access()
        assert result is False
