"""
Handler registry module - type-safe completion handler registration.

This module provides:
- TaskCompletionHandler protocol for type-safe handlers
- HandlerRegistry for managing handlers
- Global completion_handlers instance
"""

from domain.handlers.registry import (
    TaskCompletionHandler,
    HandlerRegistry,
    completion_handlers,
)

__all__ = [
    "TaskCompletionHandler",
    "HandlerRegistry",
    "completion_handlers",
]
