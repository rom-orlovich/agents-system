from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class AddCommentInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)
    comment: str = Field(..., description="Comment text", min_length=1)


class AddCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    comment_id: str | None = Field(None)
    message: str


class UpdateIssueStatusInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)
    status: Literal["resolved", "unresolved", "ignored"] = Field(
        ..., description="New status for the issue"
    )


class UpdateIssueStatusResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    message: str


class GetIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)


class SentryIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    issue_id: str | None = Field(None)
    title: str | None = Field(None)
    status: str | None = Field(None)
    level: str | None = Field(None)
    culprit: str | None = Field(None)


class AssignIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)
    assignee: str = Field(..., description="User email or team name", min_length=1)


class AssignIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    message: str


class AddTagInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)
    key: str = Field(..., description="Tag key", min_length=1)
    value: str = Field(..., description="Tag value", min_length=1)


class AddTagResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    message: str
