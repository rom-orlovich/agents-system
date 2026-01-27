"""
Task completion models - context and result for task completion handlers.

These models standardize the interface between task workers and completion handlers.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator

from domain.models.webhook_payload import WebhookSource


class TaskCompletionContext(BaseModel):
    """
    Context for task completion handlers.

    Contains all information needed to handle task completion:
    - Original payload (for routing back to source)
    - Task result/error
    - Metadata (cost, task_id, command)
    """
    # Core data
    payload: Dict[str, Any] = Field(..., description="Original webhook payload")
    message: str = Field(..., description="Formatted result message")
    success: bool = Field(..., description="Whether task succeeded")

    # Metrics
    cost_usd: float = Field(default=0.0, ge=0.0, description="Task cost in USD")

    # Identifiers
    task_id: Optional[str] = Field(None, description="Task identifier")
    command: Optional[str] = Field(None, description="Command that was executed")

    # Result data
    result: Optional[str] = Field(None, description="Full task result")
    error: Optional[str] = Field(None, description="Error message if failed")

    # Source information
    source: Optional[WebhookSource] = Field(None, description="Webhook source")

    @field_validator("cost_usd")
    @classmethod
    def validate_cost(cls, v: float) -> float:
        """Ensure cost is non-negative."""
        if v < 0:
            raise ValueError("Cost cannot be negative")
        return v

    def has_meaningful_response(self) -> bool:
        """
        Check if the task has a meaningful response to show.

        A response is meaningful if:
        - Result or message has more than 50 characters
        - Message is not just an error emoji
        """
        if self.result and len(self.result.strip()) > 50:
            return True
        if self.message and len(self.message.strip()) > 50:
            if self.message.strip() != "❌":
                return True
        return False

    def get_formatted_message(self) -> str:
        """
        Get the appropriate formatted message based on success/failure.

        For failures with error, use the error message.
        Otherwise use the standard message.
        """
        if not self.success and self.error:
            return self.error
        return self.message

    def get_routing(self) -> dict:
        """Extract routing metadata from payload."""
        return self.payload.get("routing", {})

    def get_classification(self) -> str:
        """Extract task classification from payload."""
        return self.payload.get("classification", "SIMPLE")


class TaskCompletionResult(BaseModel):
    """
    Result of task completion handling.

    Captures what actions were taken during completion handling.
    """
    comment_posted: bool = Field(default=False, description="Whether comment was posted to source")
    notification_sent: bool = Field(default=False, description="Whether Slack notification was sent")
    comment_id: Optional[int] = Field(None, description="ID of posted comment")
    error_reaction_added: bool = Field(default=False, description="Whether error reaction was added")
    approval_message_sent: bool = Field(default=False, description="Whether approval message was sent")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    @classmethod
    def success(cls, comment_id: Optional[int] = None) -> "TaskCompletionResult":
        """Create a successful completion result."""
        return cls(
            comment_posted=True,
            notification_sent=True,
            comment_id=comment_id,
        )

    @classmethod
    def failure(cls, error_reaction_added: bool = False) -> "TaskCompletionResult":
        """Create a failure completion result."""
        return cls(
            comment_posted=False,
            notification_sent=True,
            error_reaction_added=error_reaction_added,
        )
