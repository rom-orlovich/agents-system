"""Webhook observability - comprehensive logging and error tracking."""
import traceback
import sys
from functools import wraps
from typing import Any, Callable
import structlog

logger = structlog.get_logger()


def log_webhook_error(error: Exception, context: dict, operation: str):
    """Log webhook error with full stack trace and context."""
    error_details = {
        "event": "webhook_error",
        "operation": operation,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "stack_trace": traceback.format_exc(),
    }

    logger.error(**error_details)

    return error_details


def with_error_logging(operation: str):
    """Decorator to add comprehensive error logging to webhook functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            context = {
                "function": func.__name__,
                "module": func.__module__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }

            try:
                logger.debug(
                    "webhook_operation_start",
                    operation=operation,
                    function=func.__name__
                )

                result = await func(*args, **kwargs)

                logger.debug(
                    "webhook_operation_success",
                    operation=operation,
                    function=func.__name__
                )

                return result

            except Exception as e:
                log_webhook_error(e, context, operation)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            context = {
                "function": func.__name__,
                "module": func.__module__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }

            try:
                logger.debug(
                    "webhook_operation_start",
                    operation=operation,
                    function=func.__name__
                )

                result = func(*args, **kwargs)

                logger.debug(
                    "webhook_operation_success",
                    operation=operation,
                    function=func.__name__
                )

                return result

            except Exception as e:
                log_webhook_error(e, context, operation)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_webhook_request(webhook_name: str, event_type: str, payload_summary: dict):
    """Log incoming webhook request with payload summary."""
    logger.info(
        "webhook_request_received",
        webhook=webhook_name,
        event_type=event_type,
        payload_keys=list(payload_summary.keys()) if isinstance(payload_summary, dict) else None
    )


def log_webhook_response(webhook_name: str, success: bool, duration_ms: float, details: dict = None):
    """Log webhook response with timing and status."""
    logger.info(
        "webhook_response_sent",
        webhook=webhook_name,
        success=success,
        duration_ms=duration_ms,
        details=details or {}
    )


def log_handler_call(handler_name: str, method: str, params: dict = None):
    """Log handler method call."""
    logger.debug(
        "webhook_handler_call",
        handler=handler_name,
        method=method,
        params=params or {}
    )


import asyncio
