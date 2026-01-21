"""Core modules."""

from .config import settings
from .registry import Registry
from .cli_runner import run_claude_cli, CLIResult
from .background_manager import BackgroundTaskManager
from .websocket_hub import WebSocketHub
from .logging_config import setup_logging
from .exceptions import (
    AgentError,
    AuthenticationError,
    TaskError,
    WebhookError,
    agent_error_handler,
    auth_error_handler,
    task_error_handler,
)

__all__ = [
    "settings",
    "Registry",
    "run_claude_cli",
    "CLIResult",
    "BackgroundTaskManager",
    "WebSocketHub",
    "setup_logging",
    "AgentError",
    "AuthenticationError",
    "TaskError",
    "WebhookError",
    "agent_error_handler",
    "auth_error_handler",
    "task_error_handler",
]
