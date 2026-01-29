from pydantic import BaseModel, Field, ConfigDict


class PostPRCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    owner: str = Field(..., description="Repository owner", min_length=1)
    repo: str = Field(..., description="Repository name", min_length=1)
    pr_number: int = Field(..., description="Pull request number", gt=0)
    comment: str = Field(
        ..., description="Comment body", min_length=1, max_length=65536
    )


class PostPRCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    comment_id: int | None = Field(None)
    message: str
    error: str | None = Field(None)


class PostIssueCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    owner: str = Field(..., description="Repository owner", min_length=1)
    repo: str = Field(..., description="Repository name", min_length=1)
    issue_number: int = Field(..., description="Issue number", gt=0)
    comment: str = Field(
        ..., description="Comment body", min_length=1, max_length=65536
    )


class PostIssueCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    comment_id: int | None = Field(None)
    message: str
    error: str | None = Field(None)


class GetPRDetailsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    pr_number: int | None = Field(None)
    title: str | None = Field(None)
    body: str | None = Field(None)
    state: str | None = Field(None)
    merged: bool | None = Field(None)
    error: str | None = Field(None)


class GetIssueDetailsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    issue_number: int | None = Field(None)
    title: str | None = Field(None)
    body: str | None = Field(None)
    state: str | None = Field(None)
    error: str | None = Field(None)
