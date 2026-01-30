from pydantic import BaseModel, Field, ConfigDict


class AddCommentInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key (e.g., PROJ-123)", min_length=1)
    comment: str = Field(..., description="Comment body", min_length=1)


class AddCommentResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    comment_id: str | None = Field(None)
    message: str


class GetIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key", min_length=1)


class JiraIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    issue_key: str | None = Field(None)
    title: str | None = Field(None)
    status: str | None = Field(None)
    description: str | None = Field(None)


class CreateIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_key: str = Field(..., description="Project key", min_length=1)
    summary: str = Field(..., description="Issue summary", min_length=1)
    description: str = Field(..., description="Issue description")
    issue_type: str = Field(..., description="Issue type (Bug, Task, Story, etc.)", min_length=1)


class CreateIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    issue_key: str | None = Field(None)
    message: str


class TransitionIssueInput(BaseModel):
    model_config = ConfigDict(strict=True)

    issue_key: str = Field(..., description="Jira issue key", min_length=1)
    transition_id: str = Field(..., description="Transition ID to execute", min_length=1)


class TransitionIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    message: str
