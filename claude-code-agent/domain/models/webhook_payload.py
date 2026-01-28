from enum import StrEnum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WebhookSource(StrEnum):
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"


class GitHubWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    repository: Dict[str, Any]
    comment: Optional[Dict[str, Any]] = None
    issue: Optional[Dict[str, Any]] = None
    pull_request: Optional[Dict[str, Any]] = None
    sender: Optional[Dict[str, Any]] = None
    action: Optional[str] = None
    routing: Optional[Dict[str, Any]] = None
    classification: str = "SIMPLE"
    user_content: Optional[str] = Field(None, alias="_user_content")
    provider: str = "github"

    def get_owner(self) -> str:
        return self.repository.get("owner", {}).get("login", "")

    def get_repo_name(self) -> str:
        return self.repository.get("name", "")

    def get_full_repo_name(self) -> str:
        owner = self.get_owner()
        repo = self.get_repo_name()
        return f"{owner}/{repo}" if owner and repo else ""

    def get_comment_id(self) -> Optional[int]:
        if self.comment:
            return self.comment.get("id")
        return None

    def get_comment_body(self) -> str:
        if self.comment:
            return self.comment.get("body", "")
        return ""

    def get_issue_or_pr_number(self) -> Optional[int]:
        if self.issue:
            return self.issue.get("number")
        if self.pull_request:
            return self.pull_request.get("number")
        return None

    def get_sender_login(self) -> str:
        if self.sender:
            return self.sender.get("login", "")
        return ""

    def get_sender_type(self) -> str:
        if self.sender:
            return self.sender.get("type", "")
        return ""

    def is_pr_context(self) -> bool:
        if self.pull_request:
            return True
        if self.issue:
            return self.issue.get("pull_request") is not None
        return False


class JiraWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    issue: Dict[str, Any]
    comment: Optional[Dict[str, Any]] = None
    changelog: Optional[Dict[str, Any]] = None
    user: Optional[Dict[str, Any]] = None
    webhookEvent: Optional[str] = None
    routing: Optional[Dict[str, Any]] = None
    source_metadata: Optional[Dict[str, Any]] = None
    user_content: Optional[str] = Field(None, alias="_user_content")
    provider: str = "jira"

    def get_ticket_key(self) -> str:
        return self.issue.get("key", "unknown")

    def get_issue_id(self) -> Optional[str]:
        return self.issue.get("id")

    def get_summary(self) -> str:
        fields = self.issue.get("fields", {})
        return fields.get("summary", "")

    def get_description(self) -> str:
        fields = self.issue.get("fields", {})
        description = fields.get("description", "")
        return self._safe_string(description)

    def get_comment_body(self) -> str:
        if self.comment:
            body = self.comment.get("body", "")
            return self._safe_string(body)
        return ""

    def get_user_request(self) -> str:
        if self.user_content:
            return self.user_content
        if self.comment and self.comment.get("body"):
            return self.get_comment_body()
        description = self.get_description()
        if description:
            return description
        return self.get_summary()

    @staticmethod
    def _safe_string(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            if "content" in value:
                return JiraWebhookPayload._extract_adf_text(value.get("content", []))
            if "text" in value:
                return value.get("text", "")
        return str(value)

    @staticmethod
    def _extract_adf_text(content: List) -> str:
        texts = []
        for item in content:
            if isinstance(item, dict):
                if "text" in item:
                    texts.append(item["text"])
                elif "content" in item:
                    texts.append(JiraWebhookPayload._extract_adf_text(item["content"]))
        return " ".join(texts)


class SlackWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    event: Dict[str, Any]
    type: Optional[str] = None
    team_id: Optional[str] = None
    routing: Optional[Dict[str, Any]] = None
    classification: str = "SIMPLE"
    user_content: Optional[str] = Field(None, alias="_user_content")
    provider: str = "slack"

    def get_channel(self) -> Optional[str]:
        return self.event.get("channel")

    def get_thread_ts(self) -> Optional[str]:
        return self.event.get("ts")

    def get_text(self) -> str:
        return self.event.get("text", "")

    def get_user(self) -> Optional[str]:
        return self.event.get("user")

    def get_event_type(self) -> str:
        return self.event.get("type", "")

    def is_bot_message(self) -> bool:
        return self.event.get("bot_id") is not None or self.event.get("subtype") == "bot_message"
