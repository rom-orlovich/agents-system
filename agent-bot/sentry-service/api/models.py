from pydantic import BaseModel, Field, ConfigDict


class AddCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)
    comment: str = Field(..., description="Comment text", min_length=1)


class AddCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    comment_id: str | None = Field(None)
    message: str
    error: str | None = Field(None)


class UpdateIssueStatusRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_id: str = Field(..., description="Sentry issue ID", min_length=1)
    status: str = Field(..., description="Status (resolved, ignored, unresolved)")


class UpdateIssueStatusResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    message: str
    error: str | None = Field(None)


class GetIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    issue_id: str | None = Field(None)
    title: str | None = Field(None)
    culprit: str | None = Field(None)
    status: str | None = Field(None)
    level: str | None = Field(None)
    error: str | None = Field(None)
