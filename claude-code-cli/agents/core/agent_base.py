"""
Base classes for agent handlers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid


class AgentCapability(str, Enum):
    """Agent capabilities enumeration."""

    PLANNING = "planning"
    EXECUTION = "execution"
    DISCOVERY = "discovery"
    REVIEW = "review"
    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    ENRICHMENT = "enrichment"


class AgentMetadata(BaseModel):
    """Metadata for agent registration."""

    name: str = Field(..., description="Unique agent name (e.g., 'planning-agent')")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="What this agent does")
    capabilities: List[AgentCapability] = Field(..., description="Agent capabilities")
    version: str = Field(default="1.0.0", description="Agent version")
    enabled: bool = Field(default=True, description="Whether agent is enabled")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    timeout_seconds: int = Field(default=3600, description="Maximum execution time")


class AgentContext(BaseModel):
    """Context passed to agent for execution."""

    task_id: str = Field(..., description="Task ID being processed")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session ID for this execution"
    )
    task: Dict[str, Any] = Field(..., description="Full task data")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific config")
    previous_result: Optional[Any] = Field(None, description="Result from previous agent in chain")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        arbitrary_types_allowed = True


class AgentUsageMetrics(BaseModel):
    """Claude API usage metrics."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    model_used: str = ""


class AgentResult(BaseModel):
    """Standardized agent result."""

    success: bool = Field(..., description="Whether execution succeeded")
    agent_name: str = Field(..., description="Name of agent that executed")
    session_id: str = Field(..., description="Session ID for this execution")
    output: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific output")
    error: Optional[str] = Field(None, description="Error message if failed")
    next_agent: Optional[str] = Field(None, description="Next agent to chain to")

    # Timing metrics
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Usage metrics
    usage: AgentUsageMetrics = Field(default_factory=AgentUsageMetrics)

    class Config:
        arbitrary_types_allowed = True

    def set_completed(self):
        """Mark result as completed and calculate duration."""
        self.completed_at = datetime.now()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()


class BaseAgent(ABC):
    """
    Base class for all sub-agents.

    To create a new agent:
    1. Inherit from this class
    2. Implement metadata property and execute() method
    3. Place in sub_agents/ directory
    4. It will be auto-discovered and registered
    """

    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """
        Return agent metadata for registration.

        Returns:
            AgentMetadata with name, capabilities, etc.
        """
        pass

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's main logic.

        Args:
            context: AgentContext with task data, config, etc.

        Returns:
            AgentResult with output, metrics, etc.
        """
        pass

    async def pre_execute(self, context: AgentContext) -> bool:
        """
        Pre-execution validation.

        Override to add custom validation logic.

        Args:
            context: AgentContext with task data

        Returns:
            True to proceed with execution, False to skip
        """
        return True

    async def post_execute(self, result: AgentResult) -> AgentResult:
        """
        Post-execution processing.

        Override to add custom post-processing logic.

        Args:
            result: AgentResult from execute()

        Returns:
            Potentially modified AgentResult
        """
        return result

    async def on_error(self, context: AgentContext, error: Exception) -> AgentResult:
        """
        Error handling.

        Override for custom error handling logic.

        Args:
            context: AgentContext with task data
            error: Exception that occurred

        Returns:
            AgentResult with error details
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Agent {self.metadata.name} failed: {error}")

        return AgentResult(
            success=False,
            agent_name=self.metadata.name,
            session_id=context.session_id,
            output={},
            error=str(error),
            usage=AgentUsageMetrics()
        )

    async def should_retry(self, context: AgentContext, error: Exception, retry_count: int) -> bool:
        """
        Determine if should retry after error.

        Override for custom retry logic.

        Args:
            context: AgentContext with task data
            error: Exception that occurred
            retry_count: Number of retries so far

        Returns:
            True to retry, False to fail
        """
        # Default: retry up to max_retries for network/timeout errors
        if retry_count >= self.metadata.max_retries:
            return False

        # Retry on common transient errors
        error_str = str(error).lower()
        retryable_errors = ["timeout", "connection", "rate limit", "503", "502", "500"]

        return any(err in error_str for err in retryable_errors)
