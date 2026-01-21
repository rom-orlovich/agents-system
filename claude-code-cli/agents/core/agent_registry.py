"""
Central registry for agent handlers.
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
import json

from .agent_base import (
    BaseAgent,
    AgentMetadata,
    AgentCapability,
    AgentContext,
    AgentResult,
)
from .agent_metrics import AgentMetricsTracker

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for all agents.

    Provides:
    - Registration of agent handlers
    - Auto-discovery of handlers in sub_agents/ directory
    - Handler lookup by name or capability
    - Execution tracking and metrics
    """

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._enabled_count = 0
        self._disabled_count = 0
        self._execution_history: List[Dict[str, Any]] = []
        self._metrics_tracker = AgentMetricsTracker()

    def register(self, agent: BaseAgent) -> None:
        """
        Register an agent.

        Args:
            agent: Instance of BaseAgent subclass
        """
        metadata = agent.metadata

        if not metadata.enabled:
            logger.info(
                f"Agent '{metadata.name}' is disabled (set enabled=True to enable)"
            )
            self._disabled_count += 1
            return

        if metadata.name in self._agents:
            logger.warning(
                f"Agent '{metadata.name}' already registered, overwriting"
            )

        self._agents[metadata.name] = agent
        self._enabled_count += 1

        logger.info(
            f"✓ Registered agent: {metadata.name} ({metadata.display_name}) "
            f"[{', '.join(c.value for c in metadata.capabilities)}]"
        )

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Get agent by name.

        Args:
            name: Agent name (e.g., 'planning-agent')

        Returns:
            Agent instance, or None if not found
        """
        return self._agents.get(name)

    def list_agents(self) -> List[AgentMetadata]:
        """
        List all registered agent metadata.

        Returns:
            List of AgentMetadata for all registered agents
        """
        return [agent.metadata for agent in self._agents.values()]

    def get_agent_names(self) -> List[str]:
        """
        Get list of all registered agent names.

        Returns:
            List of agent names
        """
        return list(self._agents.keys())

    def get_agents_by_capability(self, capability: AgentCapability) -> List[BaseAgent]:
        """
        Get all agents with specific capability.

        Args:
            capability: AgentCapability to filter by

        Returns:
            List of agents with that capability
        """
        return [
            agent for agent in self._agents.values()
            if capability in agent.metadata.capabilities
        ]

    def get_stats(self) -> Dict[str, int]:
        """
        Get registry statistics.

        Returns:
            Dict with enabled, disabled, and total counts
        """
        return {
            "enabled": self._enabled_count,
            "disabled": self._disabled_count,
            "total": self._enabled_count + self._disabled_count,
        }

    async def execute_agent(
        self,
        agent_name: str,
        context: AgentContext,
        track_metrics: bool = True
    ) -> AgentResult:
        """
        Execute an agent and track metrics.

        Args:
            agent_name: Name of agent to execute
            context: AgentContext with task data
            track_metrics: Whether to track metrics (default: True)

        Returns:
            AgentResult from agent execution

        Raises:
            ValueError: If agent not found
        """
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found in registry")

        logger.info(
            f"Executing agent '{agent_name}' for task {context.task_id} "
            f"(session: {context.session_id})"
        )

        start_time = time.time()
        retry_count = 0
        max_retries = agent.metadata.max_retries

        while retry_count <= max_retries:
            try:
                # Pre-execution check
                if not await agent.pre_execute(context):
                    logger.warning(
                        f"Agent '{agent_name}' pre-execution check failed, skipping"
                    )
                    return AgentResult(
                        success=False,
                        agent_name=agent_name,
                        session_id=context.session_id,
                        output={},
                        error="Pre-execution check failed",
                        usage=AgentUsageMetrics()
                    )

                # Execute agent
                result = await agent.execute(context)

                # Post-execution processing
                result = await agent.post_execute(result)

                # Mark as completed
                result.set_completed()

                # Track metrics
                if track_metrics:
                    duration = time.time() - start_time
                    await self._track_execution(agent_name, context, result, duration)

                logger.info(
                    f"Agent '{agent_name}' completed successfully "
                    f"(duration: {result.duration_seconds:.2f}s)"
                )

                return result

            except Exception as e:
                logger.exception(f"Agent '{agent_name}' execution failed: {e}")

                # Check if should retry
                should_retry = await agent.should_retry(context, e, retry_count)

                if should_retry and retry_count < max_retries:
                    retry_count += 1
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.info(
                        f"Retrying agent '{agent_name}' (attempt {retry_count}/{max_retries}) "
                        f"after {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                # No more retries, handle error
                result = await agent.on_error(context, e)
                result.set_completed()

                # Track failed execution
                if track_metrics:
                    duration = time.time() - start_time
                    await self._track_execution(agent_name, context, result, duration)

                return result

        # Should not reach here, but just in case
        return AgentResult(
            success=False,
            agent_name=agent_name,
            session_id=context.session_id,
            output={},
            error=f"Max retries ({max_retries}) exceeded",
            usage=AgentUsageMetrics()
        )

    async def _track_execution(
        self,
        agent_name: str,
        context: AgentContext,
        result: AgentResult,
        duration: float
    ) -> None:
        """
        Track agent execution in metrics and history.

        Args:
            agent_name: Name of agent
            context: AgentContext
            result: AgentResult
            duration: Execution duration in seconds
        """
        # Update Prometheus metrics
        await self._metrics_tracker.track_execution(
            agent_name=agent_name,
            success=result.success,
            duration=duration,
            usage=result.usage,
            task_id=context.task_id
        )

        # Store in execution history
        execution_record = {
            "agent_name": agent_name,
            "session_id": context.session_id,
            "task_id": context.task_id,
            "success": result.success,
            "duration_seconds": duration,
            "error": result.error,
            "usage": {
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "cache_read_tokens": result.usage.cache_read_tokens,
                "cache_write_tokens": result.usage.cache_write_tokens,
                "total_tokens": result.usage.total_tokens,
                "total_cost_usd": result.usage.total_cost_usd,
                "model_used": result.usage.model_used,
            },
            "timestamp": datetime.now().isoformat(),
            "next_agent": result.next_agent,
        }

        self._execution_history.append(execution_record)

        # Store in Redis for dashboard (if available)
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
            from task_queue import RedisQueue

            queue = RedisQueue()
            await queue.redis.lpush(
                f"agent_executions:{context.task_id}",
                json.dumps(execution_record)
            )

            # Keep only last 100 executions per task
            await queue.redis.ltrim(f"agent_executions:{context.task_id}", 0, 99)

        except Exception as e:
            logger.warning(f"Failed to store execution in Redis: {e}")

    def get_execution_history(
        self,
        agent_name: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get execution history.

        Args:
            agent_name: Filter by agent name
            task_id: Filter by task ID
            limit: Maximum number of records

        Returns:
            List of execution records
        """
        history = self._execution_history

        # Filter by agent_name
        if agent_name:
            history = [h for h in history if h["agent_name"] == agent_name]

        # Filter by task_id
        if task_id:
            history = [h for h in history if h["task_id"] == task_id]

        # Return most recent first, limited
        return list(reversed(history))[:limit]

    def auto_discover(self) -> None:
        """
        Auto-discover all agents in sub_agents/ directory.

        Imports the sub_agents module which should call auto_register_agents()
        and register all found agents.
        """
        try:
            # Import sub_agents module which will auto-discover agents
            from sub_agents import auto_register_agents

            auto_register_agents(self)

            stats = self.get_stats()
            logger.info(
                f"Auto-discovery complete: {stats['enabled']} enabled, "
                f"{stats['disabled']} disabled, {stats['total']} total"
            )

        except ImportError as e:
            logger.error(f"Failed to import sub_agents module: {e}")
            logger.error("Make sure sub_agents/__init__.py exists and is valid")

    def clear(self) -> None:
        """Clear all registered agents (mainly for testing)."""
        self._agents.clear()
        self._enabled_count = 0
        self._disabled_count = 0
        self._execution_history.clear()


# Import asyncio for sleep in retry logic
import asyncio

# Import AgentUsageMetrics that was missing
from .agent_base import AgentUsageMetrics

# Global registry instance
agent_registry = AgentRegistry()
