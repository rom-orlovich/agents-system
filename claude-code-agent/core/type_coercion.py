"""
Centralized type coercion utilities.

This module provides a SINGLE SOURCE OF TRUTH for type coercion across the system.
Instead of adding defensive type checks at every function, we coerce types at
SYSTEM BOUNDARIES (task_worker, webhook routes, API handlers).

Usage:
    from core.type_coercion import coerce_to_string, WebhookCompletionParams

    # At system boundaries:
    params = WebhookCompletionParams(message=raw_message, result=raw_result)
    # params.message and params.result are now guaranteed to be strings

    # Or use the function directly:
    safe_string = coerce_to_string(possibly_list_value)
"""

from typing import Any, Optional
from pydantic import BaseModel, field_validator, ConfigDict
import json


def coerce_to_string(value: Any, separator: str = "\n") -> str:
    """
    Coerce any value to a string.

    This is the SINGLE function that handles all type coercion for string values.
    Use this at system boundaries instead of adding defensive checks everywhere.

    Args:
        value: Any value (str, list, dict, None, etc.)
        separator: Separator for joining list items (default: newline)

    Returns:
        String representation of the value

    Examples:
        >>> coerce_to_string("hello")
        'hello'
        >>> coerce_to_string(["line1", "line2"])
        'line1\\nline2'
        >>> coerce_to_string(None)
        ''
        >>> coerce_to_string({"key": "value"})
        '{"key": "value"}'
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        if not value:
            return ""
        return separator.join(str(item) for item in value if item is not None)

    if isinstance(value, dict):
        try:
            return json.dumps(value, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)

    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return value.decode('utf-8', errors='replace')

    # Fallback for any other type
    try:
        return str(value)
    except Exception:
        return ""


class WebhookCompletionParams(BaseModel):
    """
    Validated parameters for webhook completion handlers.

    This Pydantic model ENFORCES string types at the system boundary.
    Use this in _invoke_completion_handler and webhook routes to ensure
    all parameters are strings before being passed to downstream functions.

    Example:
        # In task_worker._invoke_completion_handler:
        params = WebhookCompletionParams(
            message=raw_message,
            result=raw_result,
            error=raw_error
        )

        await handler(
            message=params.message,  # Guaranteed to be str
            result=params.result,    # Guaranteed to be str or None
            error=params.error       # Guaranteed to be str or None
        )
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    message: str = ""
    result: Optional[str] = None
    error: Optional[str] = None

    @field_validator('message', mode='before')
    @classmethod
    def coerce_message(cls, v: Any) -> str:
        """Coerce message to string."""
        return coerce_to_string(v)

    @field_validator('result', mode='before')
    @classmethod
    def coerce_result(cls, v: Any) -> Optional[str]:
        """Coerce result to string or None."""
        if v is None:
            return None
        coerced = coerce_to_string(v)
        return coerced if coerced else None

    @field_validator('error', mode='before')
    @classmethod
    def coerce_error(cls, v: Any) -> Optional[str]:
        """Coerce error to string or None."""
        if v is None:
            return None
        coerced = coerce_to_string(v)
        return coerced if coerced else None


class WebhookPayloadText(BaseModel):
    """
    Validated text fields extracted from webhook payloads.

    Use this when extracting text from incoming webhook payloads
    (Slack events, GitHub comments, Jira issues, etc.)
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    text: str = ""
    body: str = ""
    content: str = ""

    @field_validator('text', 'body', 'content', mode='before')
    @classmethod
    def coerce_text_field(cls, v: Any) -> str:
        """Coerce text fields to string."""
        return coerce_to_string(v)
