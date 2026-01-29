from pydantic import BaseModel, Field, ConfigDict


class AddCommentRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key", min_length=1)
    comment: str = Field(..., description="Comment body", min_length=1, max_length=65536)


class AddCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    comment_id: str | None = Field(None)
    message: str
    error: str | None = Field(None)


class GetIssueRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key", min_length=1)


class GetIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    issue_key: str | None = Field(None)
    summary: str | None = Field(None)
    description: str | None = Field(None)
    status: str | None = Field(None)
    assignee: str | None = Field(None)
    reporter: str | None = Field(None)
    error: str | None = Field(None)


class UpdateIssueStatusRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key", min_length=1)
    transition_id: str = Field(..., description="Transition ID", min_length=1)


class UpdateIssueStatusResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    message: str
    error: str | None = Field(None)


class CreateIssueRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    project_key: str = Field(..., description="Project key", min_length=1)
    summary: str = Field(..., description="Issue summary", min_length=1)
    description: str = Field(..., description="Issue description", min_length=1)
    issue_type: str = Field(..., description="Issue type (Bug, Task, Story, etc.)")


class CreateIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    issue_key: str | None = Field(None)
    issue_id: str | None = Field(None)
    message: str
    error: str | None = Field(None)
