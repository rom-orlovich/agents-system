"""Prometheus metrics for monitoring."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY


# Task metrics
tasks_started_total = Counter(
    'ai_agent_tasks_started_total',
    'Total number of tasks started',
    ['agent']
)

tasks_completed_total = Counter(
    'ai_agent_tasks_completed_total',
    'Total number of tasks completed',
    ['agent', 'status']
)

task_duration_seconds = Histogram(
    'ai_agent_task_duration_seconds',
    'Task execution duration in seconds',
    ['agent', 'status'],
    buckets=(30, 60, 120, 300, 600, 1200, 1800, 3600)
)

queue_length = Gauge(
    'ai_agent_queue_length',
    'Current queue length',
    ['queue_name']
)

errors_total = Counter(
    'ai_agent_errors_total',
    'Total number of errors',
    ['agent', 'error_type']
)

# Agent-specific metrics
discovery_confidence = Histogram(
    'ai_agent_discovery_confidence',
    'Discovery confidence score',
    buckets=(0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0)
)

approval_latency_seconds = Histogram(
    'ai_agent_approval_latency_seconds',
    'Time from plan ready to approval',
    buckets=(60, 300, 600, 1800, 3600, 7200, 86400)
)


class MetricsCollector:
    """Metrics collection helper."""

    @staticmethod
    def get_metrics() -> str:
        """Get all metrics in Prometheus format.

        Returns:
            Metrics as string
        """
        return generate_latest(REGISTRY).decode('utf-8')

    @staticmethod
    def record_task_started(agent: str):
        """Record task start.

        Args:
            agent: Agent name (planning/executor)
        """
        tasks_started_total.labels(agent=agent).inc()

    @staticmethod
    def record_task_completed(agent: str, status: str, duration: float):
        """Record task completion.

        Args:
            agent: Agent name
            status: Completion status (success/failed)
            duration: Task duration in seconds
        """
        tasks_completed_total.labels(agent=agent, status=status).inc()
        task_duration_seconds.labels(agent=agent, status=status).observe(duration)

    @staticmethod
    def record_error(agent: str, error_type: str):
        """Record an error.

        Args:
            agent: Agent name
            error_type: Type of error
        """
        errors_total.labels(agent=agent, error_type=error_type).inc()

    @staticmethod
    def update_queue_length(queue_name: str, length: int):
        """Update queue length metric.

        Args:
            queue_name: Queue name
            length: Current queue length
        """
        queue_length.labels(queue_name=queue_name).set(length)

    @staticmethod
    def record_discovery_confidence(confidence: float):
        """Record discovery confidence score.

        Args:
            confidence: Confidence value (0-1)
        """
        discovery_confidence.observe(confidence)

    @staticmethod
    def record_approval_latency(latency_seconds: float):
        """Record approval latency.

        Args:
            latency_seconds: Time from plan ready to approval
        """
        approval_latency_seconds.observe(latency_seconds)


# Global metrics instance
metrics = MetricsCollector()
