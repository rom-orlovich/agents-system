from typing import Optional
from pydantic import BaseModel, field_validator


class RoutingMetadata(BaseModel):
    repo: Optional[str] = None
    pr_number: Optional[int] = None
    ticket_key: Optional[str] = None
    slack_channel: Optional[str] = None
    slack_thread_ts: Optional[str] = None
    source: Optional[str] = None

    @field_validator("pr_number")
    @classmethod
    def validate_pr_number(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("PR number must be positive")
        return v

    def has_github_routing(self) -> bool:
        return bool(self.repo and self.pr_number)

    def has_jira_routing(self) -> bool:
        return bool(self.ticket_key)

    def has_slack_routing(self) -> bool:
        return bool(self.slack_channel)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class PRRouting(BaseModel):
    repo: str
    pr_number: int

    @field_validator("pr_number")
    @classmethod
    def validate_pr_number(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("PR number must be positive")
        return v

    def get_owner(self) -> str:
        parts = self.repo.split("/")
        return parts[0] if len(parts) >= 2 else ""

    def get_repo_name(self) -> str:
        parts = self.repo.split("/")
        return parts[1] if len(parts) >= 2 else self.repo

    def to_routing_metadata(self) -> RoutingMetadata:
        return RoutingMetadata(
            repo=self.repo,
            pr_number=self.pr_number,
            source="github",
        )
