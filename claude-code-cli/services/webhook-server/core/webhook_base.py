"""
Base classes for webhook handlers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class WebhookMetadata(BaseModel):
    """Metadata for webhook registration."""

    name: str = Field(..., description="Unique webhook name (e.g., 'jira')")
    endpoint: str = Field(..., description="Webhook endpoint path (e.g., '/webhooks/jira')")
    description: str = Field(..., description="Human-readable description")
    secret_env_var: str = Field(..., description="Environment variable for webhook secret")
    enabled: bool = Field(default=True, description="Whether webhook is enabled")


class WebhookResponse(BaseModel):
    """Standardized webhook response."""

    status: str = Field(..., description="Response status: 'queued', 'ignored', 'error'")
    task_id: Optional[str] = Field(None, description="Task ID if queued")
    message: str = Field(..., description="Human-readable message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class BaseWebhookHandler(ABC):
    """
    Base class for all webhook handlers.

    To create a new webhook handler:
    1. Inherit from this class
    2. Implement all abstract methods
    3. Place in webhooks/ directory
    4. It will be auto-discovered and registered
    """

    @property
    @abstractmethod
    def metadata(self) -> WebhookMetadata:
        """
        Return webhook metadata for registration.

        Returns:
            WebhookMetadata with name, endpoint, description, etc.
        """
        pass

    @abstractmethod
    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate webhook signature (HMAC, etc.).

        Args:
            payload: Raw webhook payload bytes
            signature: Signature from webhook headers

        Returns:
            True if signature is valid, False otherwise
        """
        pass

    @abstractmethod
    async def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse and extract relevant data from webhook payload.

        Args:
            payload: Raw webhook payload as dict

        Returns:
            Parsed data dict, or None if payload is invalid
        """
        pass

    @abstractmethod
    async def should_process(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Determine if this webhook event should be processed.

        Args:
            parsed_data: Data from parse_payload()

        Returns:
            True if should process, False to ignore
        """
        pass

    @abstractmethod
    async def handle(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """
        Process the webhook and return response.

        Args:
            parsed_data: Data from parse_payload()

        Returns:
            WebhookResponse with status, task_id, message
        """
        pass

    async def on_error(self, error: Exception) -> WebhookResponse:
        """
        Handle errors during webhook processing.

        Can be overridden for custom error handling.

        Args:
            error: Exception that occurred

        Returns:
            WebhookResponse with error status
        """
        return WebhookResponse(
            status="error",
            message=f"Webhook processing failed: {str(error)}",
            details={"error_type": type(error).__name__}
        )
