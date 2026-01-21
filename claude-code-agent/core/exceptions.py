"""Global exception handling."""

from fastapi import Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


class AgentError(Exception):
    """Base exception for agent errors."""
    def __init__(self, message: str, code: str = "AGENT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class AuthenticationError(AgentError):
    """Claude authentication failed."""
    def __init__(self, message: str = "Claude authentication required"):
        super().__init__(message, "AUTH_ERROR")


class TaskError(AgentError):
    """Task execution error."""
    def __init__(self, message: str, task_id: str):
        self.task_id = task_id
        super().__init__(message, "TASK_ERROR")


class WebhookError(AgentError):
    """Webhook processing error."""
    def __init__(self, message: str, source: str):
        self.source = source
        super().__init__(message, "WEBHOOK_ERROR")


# Exception handlers for FastAPI
async def agent_error_handler(request: Request, exc: AgentError):
    """Handle AgentError exceptions."""
    logger.error("Agent error", code=exc.code, message=exc.message)
    return JSONResponse(
        status_code=400,
        content={"error": exc.code, "message": exc.message}
    )


async def auth_error_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors."""
    logger.warning("Authentication required", message=exc.message)
    return JSONResponse(
        status_code=401,
        content={
            "error": "AUTH_REQUIRED",
            "message": exc.message,
            "action": "Upload credentials via dashboard"
        }
    )


async def task_error_handler(request: Request, exc: TaskError):
    """Handle task errors."""
    logger.error("Task error", task_id=exc.task_id, message=exc.message)
    return JSONResponse(
        status_code=400,
        content={"error": "TASK_ERROR", "message": exc.message, "task_id": exc.task_id}
    )
