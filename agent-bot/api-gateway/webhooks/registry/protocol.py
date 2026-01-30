from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class WebhookPayload(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    provider: str
    event_type: str
    installation_id: str
    organization_id: str
    raw_payload: dict
    timestamp: datetime
    metadata: dict[str, str] = {}


class WebhookResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool
    task_id: str | None = None
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


class TaskCreationRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    provider: str
    event_type: str
    installation_id: str
    organization_id: str
    input_message: str
    source_metadata: dict[str, str]
    priority: int = 2


@runtime_checkable
class WebhookHandlerProtocol(Protocol):
    async def validate(
        self, payload: bytes, headers: dict, secret: str
    ) -> bool:
        ...

    async def parse(
        self, payload: bytes, headers: dict
    ) -> WebhookPayload:
        ...

    async def should_process(self, payload: WebhookPayload) -> bool:
        ...

    async def create_task_request(
        self, payload: WebhookPayload
    ) -> TaskCreationRequest:
        ...


class SignatureValidationError(Exception):
    def __init__(self, provider: str, reason: str):
        self.provider = provider
        self.reason = reason
        super().__init__(f"Signature validation failed for {provider}: {reason}")


class PayloadParseError(Exception):
    def __init__(self, provider: str, reason: str):
        self.provider = provider
        self.reason = reason
        super().__init__(f"Payload parsing failed for {provider}: {reason}")
