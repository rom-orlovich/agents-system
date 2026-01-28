from typing import Literal, Optional
from pydantic import BaseModel


class JiraUser(BaseModel):
    self: str
    accountId: str
    emailAddress: Optional[str] = None
    displayName: str
    active: bool


class JiraProject(BaseModel):
    self: str
    id: str
    key: str
    name: str


class JiraIssueType(BaseModel):
    id: str
    name: str


class JiraStatus(BaseModel):
    id: str
    name: str


class JiraIssueFields(BaseModel):
    summary: str
    description: Optional[str] = None
    status: JiraStatus
    issuetype: JiraIssueType
    project: JiraProject


class JiraIssue(BaseModel):
    id: str
    key: str
    self: str
    fields: JiraIssueFields


class JiraComment(BaseModel):
    self: str
    id: str
    author: JiraUser
    body: str
    created: str


class JiraChangelogItem(BaseModel):
    field: str
    fieldtype: str
    from_value: Optional[str] = None
    fromString: Optional[str] = None
    to: Optional[str] = None
    toString: Optional[str] = None


class JiraChangelog(BaseModel):
    id: str
    items: list[JiraChangelogItem]


class JiraIssueEventPayload(BaseModel):
    webhookEvent: Literal[
        "jira:issue_created",
        "jira:issue_updated",
        "jira:issue_deleted",
    ]
    issue: JiraIssue
    user: JiraUser
    changelog: Optional[JiraChangelog] = None

    def extract_text(self) -> str:
        summary = self.issue.fields.summary or ""
        description = self.issue.fields.description or ""
        return f"{summary}{description}"


class JiraCommentEventPayload(BaseModel):
    webhookEvent: Literal["comment_created", "comment_updated", "comment_deleted"]
    comment: JiraComment
    issue: JiraIssue
    user: JiraUser

    def extract_text(self) -> str:
        return self.comment.body


JiraWebhookPayload = JiraIssueEventPayload | JiraCommentEventPayload


class JiraRoutingMetadata(BaseModel):
    issue_key: str
    project_key: str
    comment_id: Optional[str] = None
    user_name: Optional[str] = None
