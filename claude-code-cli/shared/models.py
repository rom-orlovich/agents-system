"""Data models for the AI Agent System."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# Import enums from canonical source
from .enums import TaskStatus, TaskSource, RiskLevel


class DiscoveryResult(BaseModel):
    """Discovery phase output."""
    repository: str
    confidence: float = Field(ge=0.0, le=1.0)
    affected_files: List[str]
    root_cause: str
    reasoning: str
    related_files: Optional[List[str]] = None


class ExecutionStep(BaseModel):
    """Single execution step."""
    order: int
    type: str  # test, implement, verify, refactor
    file: Optional[str] = None
    action: str
    code_hint: Optional[str] = None
    command: Optional[str] = None
    expected: Optional[str] = None


class ExecutionPlan(BaseModel):
    """Execution plan from planning agent."""
    summary: str
    steps: List[ExecutionStep]
    test_command: str
    estimated_minutes: int
    risk_level: RiskLevel
    risks: List[str]


class SentryAnalysis(BaseModel):
    """Sentry error analysis."""
    error_type: str
    error_message: str
    occurrences: int
    affected_users: int
    first_seen: datetime
    last_seen: datetime
    stack_trace: Dict[str, Any]
    common_patterns: List[str]
    suggested_fix: str


class ExecutionResult(BaseModel):
    """Execution phase output."""
    task_id: str
    status: TaskStatus
    results: Dict[str, Any]
    pr_url: Optional[str] = None
    execution_time: str


class Task(BaseModel):
    """Main task model."""
    task_id: str
    source: TaskSource
    status: TaskStatus

    # Input data
    description: str
    repository: Optional[str] = None
    issue_key: Optional[str] = None
    sentry_issue_id: Optional[str] = None

    # Discovery results
    discovery: Optional[DiscoveryResult] = None
    sentry_analysis: Optional[SentryAnalysis] = None

    # Planning results
    plan: Optional[ExecutionPlan] = None
    plan_url: Optional[str] = None  # GitHub PR URL

    # Execution results
    execution: Optional[ExecutionResult] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    completed_at: Optional[datetime] = None

    # Error tracking
    error: Optional[str] = None
    retry_count: int = 0


class ApprovalRequest(BaseModel):
    """Approval request model."""
    task_id: str
    approved: bool
    approved_by: str
    reason: Optional[str] = None


class WebhookPayload(BaseModel):
    """Generic webhook payload."""
    source: TaskSource
    data: Dict[str, Any]
    signature: Optional[str] = None
