from typing import Literal, Optional
from pydantic import BaseModel


class GitHubUser(BaseModel):
    login: str
    id: int
    type: str


class GitHubRepository(BaseModel):
    id: int
    name: str
    full_name: str
    owner: GitHubUser
    private: bool


class GitHubIssue(BaseModel):
    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str
    user: GitHubUser
    pull_request: Optional[dict] = None


class GitHubComment(BaseModel):
    id: int
    body: str
    user: GitHubUser
    created_at: str


class GitHubPullRequest(BaseModel):
    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str
    user: GitHubUser


class GitHubIssueCommentPayload(BaseModel):
    action: Literal["created", "edited", "deleted"]
    issue: GitHubIssue
    comment: GitHubComment
    repository: GitHubRepository
    sender: GitHubUser

    def extract_text(self) -> str:
        return self.comment.body


class GitHubIssuesPayload(BaseModel):
    action: Literal["opened", "edited", "closed", "reopened"]
    issue: GitHubIssue
    repository: GitHubRepository
    sender: GitHubUser

    def extract_text(self) -> str:
        title = self.issue.title or ""
        body = self.issue.body or ""
        return f"{title}{body}"


class GitHubPullRequestPayload(BaseModel):
    action: Literal["opened", "edited", "closed", "synchronize"]
    pull_request: GitHubPullRequest
    repository: GitHubRepository
    sender: GitHubUser

    def extract_text(self) -> str:
        title = self.pull_request.title or ""
        body = self.pull_request.body or ""
        return f"{title}{body}"


GitHubWebhookPayload = GitHubIssueCommentPayload | GitHubIssuesPayload | GitHubPullRequestPayload


class GitHubRoutingMetadata(BaseModel):
    owner: str
    repo: str
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None
    comment_id: Optional[int] = None
    sender: Optional[str] = None
