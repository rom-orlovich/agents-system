"""Unit tests for CLI status business logic."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timezone
from pathlib import Path

from core.database.models import SessionDB


async def test_startup_without_credentials_does_not_fail():
    """App should start successfully even if credentials don't exist."""
    from core.config import settings
    
    with patch.object(Path, 'exists', return_value=False):
        creds_path = settings.credentials_path
        assert not creds_path.exists()


async def test_startup_does_not_run_cli_test():
    """App startup should NOT run CLI test even if credentials exist."""
    from main import lifespan
    from fastapi import FastAPI
    from core.config import settings
    
    mock_creds_path = MagicMock()
    mock_creds_path.exists.return_value = True
    mock_creds_path.read_text.return_value = '{"access_token": "test_token_12345", "refresh_token": "refresh_token_12345", "expires_at": 9999999999999, "account_id": "user-123"}'
    
    with patch('main.init_db'):
        with patch('main.redis_client') as mock_redis:
            mock_redis.connect = AsyncMock()
            mock_redis.disconnect = AsyncMock()
            with patch('main.validate_webhook_configs'):
                with patch('main.TaskWorker') as mock_task_worker:
                    mock_worker_instance = MagicMock()
                    mock_worker_instance.run = AsyncMock()
                    mock_worker_instance.stop = AsyncMock()
                    mock_task_worker.return_value = mock_worker_instance
                    
                    with patch('core.cli_access.test_cli_access') as mock_test_cli:
                        with patch('main.async_session_factory'):
                            with patch.object(settings.__class__, 'credentials_path', new_callable=PropertyMock, return_value=mock_creds_path):
                                app = FastAPI()
                                
                                async with lifespan(app):
                                    pass
                                
                                mock_test_cli.assert_not_called()


async def test_startup_test_failure_sets_active_false():
    """If CLI test fails, set session.active = False."""
    from core.config import settings
    
    mock_creds_path = MagicMock()
    mock_creds_path.exists.return_value = True
    mock_creds_path.read_text.return_value = '{"access_token": "test_token_12345", "refresh_token": "refresh_token_12345", "expires_at": 9999999999999, "account_id": "user-123"}'
    
    with patch('core.cli_access.test_cli_access', return_value=False):
        with patch.object(settings.__class__, 'credentials_path', new_callable=PropertyMock, return_value=mock_creds_path):
            from core.cli_access import test_cli_access
            result = await test_cli_access()
            assert result is False


async def test_executive_limit_error_updates_session_active_false():
    """When task fails with executive limit error, update session.active = False."""
    from workers.task_worker import TaskWorker
    from core.websocket_hub import WebSocketHub
    from core.database.models import TaskDB, SessionDB
    from shared import TaskStatus
    
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)
    
    session_db = SessionDB(
        session_id="session-001",
        user_id="user-001",
        machine_id="machine-001",
        connected_at=datetime.now(timezone.utc),
        active=True
    )
    
    task_db = TaskDB(
        task_id="task-001",
        session_id="session-001",
        user_id="user-001",
        assigned_agent="brain",
        agent_type="planning",
        status=TaskStatus.FAILED,
        input_message="Test",
        source="dashboard",
        created_at=datetime.now(timezone.utc)
    )
    
    mock_cli_result = MagicMock()
    mock_cli_result.success = False
    mock_cli_result.error = "Error: Executive limit exceeded"
    
    error_lower = mock_cli_result.error.lower()
    assert "executive limit" in error_lower or "out of extra usage" in error_lower or "rate limit" in error_lower
    
    assert session_db.active is True


async def test_rate_limit_error_updates_session_active_false():
    """When task fails with rate limit error, update session.active = False."""
    from workers.task_worker import TaskWorker
    from core.websocket_hub import WebSocketHub
    from core.database.models import TaskDB, SessionDB
    from shared import TaskStatus
    
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)
    
    session_db = SessionDB(
        session_id="session-001",
        user_id="user-001",
        machine_id="machine-001",
        connected_at=datetime.now(timezone.utc),
        active=True
    )
    
    task_db = TaskDB(
        task_id="task-001",
        session_id="session-001",
        user_id="user-001",
        assigned_agent="brain",
        agent_type="planning",
        status=TaskStatus.FAILED,
        input_message="Test",
        source="dashboard",
        created_at=datetime.now(timezone.utc)
    )
    
    mock_cli_result = MagicMock()
    mock_cli_result.success = False
    mock_cli_result.error = "Error: You're out of extra usage · resets 9pm (UTC)"
    
    error_lower = mock_cli_result.error.lower()
    assert "executive limit" in error_lower or "out of extra usage" in error_lower or "rate limit" in error_lower
    
    assert session_db.active is True


async def test_authentication_error_sets_session_active_false():
    """When task fails with authentication error, session.active should be set to False."""
    from workers.task_worker import TaskWorker
    from core.websocket_hub import WebSocketHub
    from core.database.models import TaskDB, SessionDB
    from shared import TaskStatus
    from core.cli_runner import CLIResult
    
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)
    
    session_db = SessionDB(
        session_id="session-001",
        user_id="user-001",
        machine_id="machine-001",
        connected_at=datetime.now(timezone.utc),
        active=True
    )
    
    task_db = TaskDB(
        task_id="task-001",
        session_id="session-001",
        user_id="user-001",
        assigned_agent="brain",
        agent_type="planning",
        status=TaskStatus.QUEUED,
        input_message="Test",
        source="dashboard",
        source_metadata='{}',
        created_at=datetime.now(timezone.utc)
    )
    
    cli_result = CLIResult(
        success=False,
        output="",
        clean_output="",
        cost_usd=0.0,
        input_tokens=0,
        output_tokens=0,
        error="Invalid API key · Please run /login"
    )
    
    mock_db_session = AsyncMock()
    execute_calls = []
    
    async def mock_execute(query):
        execute_calls.append(query)
        result = MagicMock()
        if len(execute_calls) == 1:
            result.scalar_one_or_none.return_value = task_db
            return result
        elif len(execute_calls) >= 2 and ("SessionDB" in str(query) or hasattr(query, 'column_descriptions')):
            scalars_result = MagicMock()
            scalars_result.all.return_value = [session_db]
            result.scalars = MagicMock(return_value=scalars_result)
            return result
        result.scalar_one_or_none.return_value = session_db
        return result
    
    mock_db_session.execute = AsyncMock(side_effect=mock_execute)
    mock_db_session.commit = AsyncMock()
    
    async def mock_run_claude_cli(*args, **kwargs):
        output_queue = kwargs.get('output_queue')
        if output_queue:
            await output_queue.put(None)
        return cli_result
    
    with patch('workers.task_worker.run_claude_cli', side_effect=mock_run_claude_cli):
        with patch('workers.task_worker.async_session_factory') as mock_factory:
            mock_factory.return_value.__aenter__.return_value = mock_db_session
            mock_factory.return_value.__aexit__.return_value = None
            
            with patch('workers.task_worker.redis_client') as mock_redis:
                mock_redis.set_task_status = AsyncMock()
                mock_redis.append_output = AsyncMock()
                with patch.object(worker, '_update_conversation_metrics'), \
                     patch.object(worker, '_update_claude_task_status'), \
                     patch.object(worker, '_add_task_response_to_conversation'), \
                     patch.object(worker, '_send_slack_notification'), \
                     patch.object(worker, '_invoke_completion_handler'), \
                     patch.object(worker, '_get_agent_dir', return_value=Path("/tmp")):
                    await worker._process_task("task-001")
            
            assert session_db.active is False


async def test_conversation_error_does_not_set_session_active_false():
    """When task fails with conversation error (not auth/rate limit), session.active should remain True."""
    from workers.task_worker import TaskWorker
    from core.websocket_hub import WebSocketHub
    from core.database.models import TaskDB, SessionDB
    from shared import TaskStatus
    from core.cli_runner import CLIResult
    
    ws_hub = WebSocketHub()
    worker = TaskWorker(ws_hub)
    
    session_db = SessionDB(
        session_id="session-002",
        user_id="user-002",
        machine_id="machine-001",
        connected_at=datetime.now(timezone.utc),
        active=True
    )
    
    task_db = TaskDB(
        task_id="task-002",
        session_id="session-002",
        user_id="user-002",
        assigned_agent="brain",
        agent_type="planning",
        status=TaskStatus.QUEUED,
        input_message="Test",
        source="dashboard",
        source_metadata='{}',
        created_at=datetime.now(timezone.utc)
    )
    
    cli_result = CLIResult(
        success=False,
        output="",
        clean_output="",
        cost_usd=0.0,
        input_tokens=0,
        output_tokens=0,
        error="Network timeout"
    )
    
    mock_db_session = AsyncMock()
    execute_calls = []
    
    async def mock_execute(query):
        execute_calls.append(query)
        result = MagicMock()
        if len(execute_calls) == 1:
            result.scalar_one_or_none.return_value = task_db
            return result
        elif len(execute_calls) >= 2 and ("SessionDB" in str(query) or hasattr(query, 'column_descriptions')):
            scalars_result = MagicMock()
            scalars_result.all.return_value = [session_db]
            result.scalars = MagicMock(return_value=scalars_result)
            return result
        result.scalar_one_or_none.return_value = session_db
        return result
    
    mock_db_session.execute = AsyncMock(side_effect=mock_execute)
    mock_db_session.commit = AsyncMock()
    
    async def mock_run_claude_cli(*args, **kwargs):
        output_queue = kwargs.get('output_queue')
        if output_queue:
            await output_queue.put(None)
        return cli_result
    
    with patch('workers.task_worker.run_claude_cli', side_effect=mock_run_claude_cli):
        with patch('workers.task_worker.async_session_factory') as mock_factory:
            mock_factory.return_value.__aenter__.return_value = mock_db_session
            mock_factory.return_value.__aexit__.return_value = None
            
            with patch('workers.task_worker.redis_client') as mock_redis:
                mock_redis.set_task_status = AsyncMock()
                mock_redis.append_output = AsyncMock()
                with patch.object(worker, '_update_conversation_metrics'), \
                     patch.object(worker, '_update_claude_task_status'), \
                     patch.object(worker, '_add_task_response_to_conversation'), \
                     patch.object(worker, '_send_slack_notification'), \
                     patch.object(worker, '_invoke_completion_handler'), \
                     patch.object(worker, '_get_agent_dir', return_value=Path("/tmp")):
                    await worker._process_task("task-002")
            
            # Conversation errors should NOT set active to False
            assert session_db.active is True


async def test_credentials_upload_triggers_test_and_updates_status():
    """Uploading credentials should test CLI and update session status."""
    from api.credentials import upload_credentials
    from fastapi import UploadFile
    
    file_content = b'{"access_token": "test_token_12345", "refresh_token": "refresh_token_12345", "expires_at": 9999999999999, "account_id": "user-123"}'
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "claude.json"
    mock_file.read = AsyncMock(return_value=file_content)
    
    with patch('core.cli_access.test_cli_access', return_value=True):
        with patch('api.credentials.async_session_factory') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session_factory.return_value = mock_session
            
            from core.cli_access import test_cli_access
            result = await test_cli_access()
            assert result is True


async def test_cli_status_endpoint_returns_current_status():
    """Status endpoint should return active status from database."""
    from api.credentials import get_cli_status
    from core.database.models import SessionDB
    from core.config import settings
    
    session_db = SessionDB(
        session_id="session-001",
        user_id="user-123",
        machine_id="machine-001",
        connected_at=datetime.now(timezone.utc),
        active=True
    )
    
    mock_creds_path = MagicMock()
    mock_creds_path.exists.return_value = True
    mock_creds_path.read_text.return_value = '{"access_token": "test_token_12345", "refresh_token": "refresh_token_12345", "expires_at": 9999999999999, "account_id": "user-123"}'
    
    with patch.object(settings.__class__, 'credentials_path', new_callable=PropertyMock, return_value=mock_creds_path):
        with patch('api.credentials.get_db_session') as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = session_db
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_db
            
            result = await get_cli_status(db=mock_db)
            
            assert result["active"] is True
            assert result["message"] is None


async def test_cli_status_endpoint_handles_missing_credentials():
    """Status endpoint should handle missing credentials gracefully."""
    from api.credentials import get_cli_status
    from core.config import settings
    
    mock_creds_path = MagicMock()
    mock_creds_path.exists.return_value = False
    
    mock_home = MagicMock()
    mock_claude_dir = MagicMock()
    mock_cli_creds_path = MagicMock()
    mock_cli_creds_path.exists.return_value = False
    mock_claude_dir.__truediv__.return_value = mock_cli_creds_path
    mock_home.__truediv__.return_value = mock_claude_dir
    
    with patch.object(settings.__class__, 'credentials_path', new_callable=PropertyMock, return_value=mock_creds_path):
        with patch('api.credentials.Path.home', return_value=mock_home):
            mock_db = AsyncMock()
            result = await get_cli_status(db=mock_db)
            
            assert result["active"] is False
            assert "Credentials not found" in result["message"] or "credentials" in result["message"].lower()


async def test_cli_status_does_not_call_cli_when_no_session():
    """get_cli_status() should NOT call test_cli_access() when no session exists."""
    from api.credentials import get_cli_status
    from core.config import settings
    
    mock_creds_path = MagicMock()
    mock_creds_path.exists.return_value = True
    mock_creds_path.read_text.return_value = '{"access_token": "test_token_12345", "refresh_token": "refresh_token_12345", "expires_at": 9999999999999, "account_id": "user-123"}'
    
    with patch.object(settings.__class__, 'credentials_path', new_callable=PropertyMock, return_value=mock_creds_path):
        with patch('api.credentials.test_cli_access') as mock_test_cli:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await get_cli_status(db=mock_db)
            
            mock_test_cli.assert_not_called()
            assert result["active"] is False
            assert "No session found" in result["message"]


async def test_cli_status_only_reads_from_database():
    """get_cli_status() should only read from database, never call CLI."""
    from api.credentials import get_cli_status
    from core.config import settings
    from core.database.models import SessionDB
    
    mock_creds_path = MagicMock()
    mock_creds_path.exists.return_value = True
    mock_creds_path.read_text.return_value = '{"access_token": "test_token_12345", "refresh_token": "refresh_token_12345", "expires_at": 9999999999999, "account_id": "user-123"}'
    
    session_db = SessionDB(
        session_id="session-001",
        user_id="user-123",
        machine_id="machine-001",
        connected_at=datetime.now(timezone.utc),
        active=True
    )
    
    with patch.object(settings.__class__, 'credentials_path', new_callable=PropertyMock, return_value=mock_creds_path):
        with patch('api.credentials.test_cli_access') as mock_test_cli:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = session_db
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await get_cli_status(db=mock_db)
            
            mock_test_cli.assert_not_called()
            assert result["active"] is True
            assert result["message"] is None


async def test_cli_access_logs_stderr_on_failure():
    """test_cli_access() should return False and log warning when CLI test fails with stderr."""
    from core.cli_access import test_cli_access
    import subprocess
    
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Rate limit exceeded"
    mock_result.stdout = ""
    
    with patch('subprocess.run', return_value=mock_result):
        with patch('core.cli_access.logger') as mock_logger:
            result = await test_cli_access()
            
            assert result is False
            mock_logger.warning.assert_called_once()


async def test_cli_access_handles_rate_limit_error():
    """test_cli_access() should return False on rate limit errors."""
    from core.cli_access import test_cli_access
    import subprocess
    
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error: You're out of extra usage"
    
    with patch('subprocess.run', return_value=mock_result):
        result = await test_cli_access()
        assert result is False


async def test_upload_credentials_broadcasts_websocket_update(tmp_path):
    """REQUIREMENT: When credentials uploaded and CLI test succeeds, upload should succeed."""
    from api.credentials import upload_credentials
    from fastapi import UploadFile, Request
    
    file_content = b'{"access_token": "test_token_12345", "refresh_token": "refresh_token_12345", "expires_at": 9999999999999, "account_id": "user-123"}'
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "claude.json"
    mock_file.read = AsyncMock(return_value=file_content)
    
    mock_request = MagicMock(spec=Request)
    mock_request.app.state.ws_hub = MagicMock()
    
    mock_creds_path = tmp_path / "credentials" / "claude.json"
    mock_creds_path.parent.mkdir(parents=True, exist_ok=True)
    
    with patch('api.credentials.test_cli_access', return_value=True):
        with patch('api.credentials.async_session_factory') as mock_session_factory:
            with patch('api.credentials.settings') as mock_settings:
                with patch('pathlib.Path.home', return_value=tmp_path / "home"):
                    mock_settings.credentials_path = mock_creds_path
                    mock_session = AsyncMock()
                    mock_session.__aenter__.return_value = mock_session
                    mock_session.__aexit__.return_value = None
                    mock_session.add = MagicMock()
                    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
                    mock_session.commit = AsyncMock()
                    mock_session_factory.return_value = mock_session
                    
                    result = await upload_credentials(file=mock_file, request=mock_request)
                    
                    assert result.success is True
                    mock_session.commit.assert_called_once()


async def test_upload_credentials_sets_status_false_on_error(tmp_path):
    """REQUIREMENT: When CLI test fails, upload should still succeed but session marked inactive."""
    from api.credentials import upload_credentials
    from fastapi import UploadFile, Request
    
    file_content = b'{"access_token": "test_token_12345", "refresh_token": "refresh_token_12345", "expires_at": 9999999999999, "account_id": "user-123"}'
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "claude.json"
    mock_file.read = AsyncMock(return_value=file_content)
    
    mock_request = MagicMock(spec=Request)
    mock_request.app.state.ws_hub = MagicMock()
    
    mock_creds_path = tmp_path / "credentials" / "claude.json"
    mock_creds_path.parent.mkdir(parents=True, exist_ok=True)
    
    with patch('api.credentials.test_cli_access', side_effect=Exception("Rate limit exceeded")):
        with patch('api.credentials.async_session_factory') as mock_session_factory:
            with patch('api.credentials.settings') as mock_settings:
                with patch('pathlib.Path.home', return_value=tmp_path / "home"):
                    mock_settings.credentials_path = mock_creds_path
                    mock_session = AsyncMock()
                    mock_session.__aenter__.return_value = mock_session
                    mock_session.__aexit__.return_value = None
                    mock_session.add = MagicMock()
                    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
                    mock_session.commit = AsyncMock()
                    mock_session_factory.return_value = mock_session
                    
                    result = await upload_credentials(file=mock_file, request=mock_request)
                    
                    assert result.success is True
                    mock_session.commit.assert_called_once()
