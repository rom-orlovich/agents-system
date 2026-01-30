"""Agent container entry point."""

import asyncio
import os
import signal
import structlog
from core.queue_manager import QueueManager
from core.worker import Worker

logger = structlog.get_logger()


async def main() -> None:
    """Main entry point."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    queue_name = os.getenv("QUEUE_NAME", "planning_tasks")

    queue_manager = QueueManager(redis_url)
    await queue_manager.connect()

    worker = Worker(queue_manager, queue_name)

    def shutdown_handler(sig: int, frame: Any) -> None:
        logger.info("shutdown_signal_received", signal=sig)
        asyncio.create_task(worker.stop())

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("agent_container_starting")

    try:
        await worker.start()
    finally:
        await queue_manager.disconnect()
        logger.info("agent_container_stopped")


if __name__ == "__main__":
    asyncio.run(main())
