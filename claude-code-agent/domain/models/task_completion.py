from typing import Any, Dict, Optional
from pydantic import BaseModel, field_validator

from domain.models.webhook_payload import WebhookSource


class TaskCompletionContext(BaseModel):
    payload: Dict[str, Any]
    message: str
    success: bool
    cost_usd: float = 0.0
    task_id: Optional[str] = None
    command: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    source: Optional[WebhookSource] = None

    @field_validator("cost_usd")
    @classmethod
    def validate_cost(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Cost cannot be negative")
        return v

    def has_meaningful_response(self) -> bool:
        if self.result and len(self.result.strip()) > 50:
            return True
        if self.message and len(self.message.strip()) > 50:
            if self.message.strip() != "❌":
                return True
        return False

    def get_formatted_message(self) -> str:
        if not self.success and self.error:
            return self.error
        return self.message

    def get_routing(self) -> dict:
        return self.payload.get("routing", {})

    def get_classification(self) -> str:
        return self.payload.get("classification", "SIMPLE")


class TaskCompletionResult(BaseModel):
    comment_posted: bool = False
    notification_sent: bool = False
    comment_id: Optional[int] = None
    error_reaction_added: bool = False
    approval_message_sent: bool = False

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def success(cls, comment_id: Optional[int] = None) -> "TaskCompletionResult":
        return cls(
            comment_posted=True,
            notification_sent=True,
            comment_id=comment_id,
        )

    @classmethod
    def failure(cls, error_reaction_added: bool = False) -> "TaskCompletionResult":
        return cls(
            comment_posted=False,
            notification_sent=True,
            error_reaction_added=error_reaction_added,
        )
