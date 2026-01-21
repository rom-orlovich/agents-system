"""
Agent-specific metrics tracking.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AgentMetricsTracker:
    """
    Tracks agent execution metrics using Prometheus.

    Metrics tracked:
    - Execution count (success/failed)
    - Execution duration
    - Cost per agent
    - Token usage
    - Active sessions
    """

    def __init__(self):
        self._metrics_available = False
        self._init_metrics()

    def _init_metrics(self):
        """Initialize Prometheus metrics if available."""
        try:
            from prometheus_client import Counter, Histogram, Gauge

            # Agent execution counter
            self.execution_counter = Counter(
                'ai_agent_execution_total',
                'Total agent executions',
                ['agent', 'status', 'task_type']
            )

            # Agent execution duration
            self.execution_duration = Histogram(
                'ai_agent_execution_duration_seconds',
                'Agent execution duration in seconds',
                ['agent', 'task_type'],
                buckets=(30, 60, 120, 300, 600, 1200, 1800, 3600)
            )

            # Agent cost tracking
            self.cost_counter = Counter(
                'ai_agent_cost_total_usd',
                'Total cost in USD per agent',
                ['agent', 'model']
            )

            # Token usage tracking
            self.token_counter = Counter(
                'ai_agent_tokens_total',
                'Total tokens used per agent',
                ['agent', 'token_type']  # input/output/cache_read/cache_write
            )

            # Active sessions
            self.active_sessions = Gauge(
                'ai_agent_sessions_active',
                'Currently active agent sessions',
                ['agent']
            )

            # Session duration
            self.session_duration = Histogram(
                'ai_agent_session_duration_seconds',
                'Session duration from start to completion',
                ['agent', 'task_type'],
                buckets=(60, 300, 600, 1200, 1800, 3600, 7200)
            )

            self._metrics_available = True
            logger.info("Agent metrics initialized successfully")

        except ImportError:
            logger.warning(
                "Prometheus client not available, metrics tracking disabled"
            )
            self._metrics_available = False

    async def track_execution(
        self,
        agent_name: str,
        success: bool,
        duration: float,
        usage: "AgentUsageMetrics",
        task_id: Optional[str] = None
    ):
        """
        Track agent execution metrics.

        Args:
            agent_name: Name of agent
            success: Whether execution succeeded
            duration: Execution duration in seconds
            usage: AgentUsageMetrics with token/cost data
            task_id: Optional task ID
        """
        if not self._metrics_available:
            return

        try:
            # Extract task type from task_id if available
            task_type = "unknown"
            if task_id:
                # Task ID format: {source}_{action}_{timestamp}
                parts = task_id.split("_")
                if len(parts) >= 2:
                    task_type = f"{parts[0]}_{parts[1]}"

            # Update execution counter
            status = "success" if success else "failed"
            self.execution_counter.labels(
                agent=agent_name,
                status=status,
                task_type=task_type
            ).inc()

            # Update duration histogram
            self.execution_duration.labels(
                agent=agent_name,
                task_type=task_type
            ).observe(duration)

            # Update cost counter
            if usage.total_cost_usd > 0:
                self.cost_counter.labels(
                    agent=agent_name,
                    model=usage.model_used or "unknown"
                ).inc(usage.total_cost_usd)

            # Update token counters
            if usage.input_tokens > 0:
                self.token_counter.labels(
                    agent=agent_name,
                    token_type="input"
                ).inc(usage.input_tokens)

            if usage.output_tokens > 0:
                self.token_counter.labels(
                    agent=agent_name,
                    token_type="output"
                ).inc(usage.output_tokens)

            if usage.cache_read_tokens > 0:
                self.token_counter.labels(
                    agent=agent_name,
                    token_type="cache_read"
                ).inc(usage.cache_read_tokens)

            if usage.cache_write_tokens > 0:
                self.token_counter.labels(
                    agent=agent_name,
                    token_type="cache_write"
                ).inc(usage.cache_write_tokens)

            # Update session duration
            self.session_duration.labels(
                agent=agent_name,
                task_type=task_type
            ).observe(duration)

        except Exception as e:
            logger.warning(f"Failed to track agent metrics: {e}")

    def increment_active_sessions(self, agent_name: str):
        """Increment active sessions counter."""
        if self._metrics_available:
            self.active_sessions.labels(agent=agent_name).inc()

    def decrement_active_sessions(self, agent_name: str):
        """Decrement active sessions counter."""
        if self._metrics_available:
            self.active_sessions.labels(agent=agent_name).dec()


# Import AgentUsageMetrics type hint
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .agent_base import AgentUsageMetrics
