"""Shared models and utilities."""

from .machine_models import (
    # Enums
    TaskStatus,
    AgentType,
    EntityType,
    AuthStatus,
    # Core Models
    MachineConfig,
    Session,
    Task,
    SubAgentConfig,
    WebhookConfig,
    WebhookCommand,
    SkillConfig,
    ClaudeCredentials,
    # WebSocket Messages
    WebSocketMessage,
    TaskCreatedMessage,
    TaskOutputMessage,
    TaskMetricsMessage,
    TaskCompletedMessage,
    TaskFailedMessage,
    UserInputMessage,
    TaskStopMessage,
    ChatMessage,
    WSMessage,
    # Request/Response
    CreateWebhookRequest,
    CreateAgentRequest,
    UploadCredentialsRequest,
    APIResponse,
)

__all__ = [
    # Enums
    "TaskStatus",
    "AgentType",
    "EntityType",
    "AuthStatus",
    # Core Models
    "MachineConfig",
    "Session",
    "Task",
    "SubAgentConfig",
    "WebhookConfig",
    "WebhookCommand",
    "SkillConfig",
    "ClaudeCredentials",
    # WebSocket Messages
    "WebSocketMessage",
    "TaskCreatedMessage",
    "TaskOutputMessage",
    "TaskMetricsMessage",
    "TaskCompletedMessage",
    "TaskFailedMessage",
    "UserInputMessage",
    "TaskStopMessage",
    "ChatMessage",
    "WSMessage",
    # Request/Response
    "CreateWebhookRequest",
    "CreateAgentRequest",
    "UploadCredentialsRequest",
    "APIResponse",
]
