import asyncio
import os
from pathlib import Path

import structlog

from container import create_container, ContainerConfig
from core.repo_manager import RepoManager
from core.streaming_logger import StreamingLogger
from core.result_poster import ResultPoster, WebhookProvider
from core.mcp_client import MCPClient

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
database_url = os.getenv(
    "DATABASE_URL", "postgresql://agent:agent@localhost:5432/agent_bot"
)
worker_id = f"worker-{os.getpid()}"


async def process_task(task, container):
    task_id = task.task_id
    streaming_logger = StreamingLogger(task_id)

    await streaming_logger.log_progress(
        stage="initialization", message="Task received by worker"
    )

    try:
        installation = await container.token_service.get_installation(
            task.installation_id
        )

        await streaming_logger.log_progress(
            stage="repository", message="Cloning or updating repository"
        )

        repo_manager = RepoManager(base_path=Path("/tmp/repos"))

        if "repo" in task.source_metadata:
            repo_name = task.source_metadata["repo"]
            repo_path = await repo_manager.ensure_repo(
                repo_url=f"https://github.com/{repo_name}.git",
                token=installation.access_token,
            )

            await streaming_logger.log_progress(
                stage="repository",
                message=f"Repository ready at {repo_path}",
                success=True,
            )
        else:
            repo_path = Path("/tmp/workdir")
            repo_path.mkdir(parents=True, exist_ok=True)

        await streaming_logger.log_progress(
            stage="execution", message="Executing Claude CLI"
        )

        result = await container.cli_runner.execute_and_wait(
            command=["claude", "chat"],
            input_text=task.input_message,
            timeout_seconds=300,
        )

        await streaming_logger.log_progress(
            stage="execution",
            message="CLI execution completed",
            success=result.success,
        )

        if result.success and task.source_metadata.get("provider"):
            await streaming_logger.log_progress(
                stage="posting_result",
                message=f"Posting result to {task.provider}",
            )

            try:
                provider = WebhookProvider(task.provider)
                mcp_client = MCPClient()
                result_poster = ResultPoster(mcp_client)

                posted = await result_poster.post_result(
                    provider=provider,
                    metadata=task.source_metadata,
                    result=result.output,
                )

                if posted:
                    await streaming_logger.log_progress(
                        stage="posting_result",
                        message="Result posted successfully",
                        success=True,
                    )
            except Exception as e:
                logger.error(
                    "result_posting_error", task_id=task_id, error=str(e)
                )
                await streaming_logger.log_error(
                    error=f"Result posting failed: {str(e)}"
                )

        await streaming_logger.log_completion(
            success=result.success,
            result=result.output if result.success else None,
            error=result.error,
        )

        await container.queue.ack(task_id)

    except Exception as e:
        logger.error("task_processing_failed", task_id=task_id, error=str(e))
        await streaming_logger.log_error(error=str(e))
        await streaming_logger.log_completion(success=False, error=str(e))
        await container.queue.nack(task_id)


async def main():
    config = ContainerConfig(
        queue_type="redis",
        cache_type="memory",
        database_type="postgres",
        cli_type="real",
        redis_url=redis_url,
        database_url=database_url,
    )

    container = await create_container(config)

    logger.info("task_worker_started", worker_id=worker_id)

    while True:
        try:
            task = await container.queue.dequeue(timeout_seconds=5.0)

            if task is None:
                continue

            logger.info(
                "task_dequeued",
                task_id=task.task_id,
                worker_id=worker_id,
                priority=task.priority.name,
            )

            await process_task(task, container)

        except KeyboardInterrupt:
            logger.info("worker_shutting_down", worker_id=worker_id)
            break
        except Exception as e:
            logger.error("worker_error", worker_id=worker_id, error=str(e))
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
