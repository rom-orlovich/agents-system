import asyncio
import os
from pathlib import Path
from datetime import datetime, timezone

import structlog

from container import create_container, ContainerConfig
from core.repo_manager import RepoManager
from core.streaming_logger import StreamingLogger
from core.result_poster import ResultPoster, WebhookProvider
from core.mcp_client import MCPClient
from core.agents.models import AgentTask, AgentContext

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
    start_time = datetime.now(timezone.utc)

    await streaming_logger.log_progress(
        stage="initialization", message="Task received by worker"
    )

    try:
        installation = await container.token_service.get_installation(
            task.installation_id
        )

        if hasattr(container, "conversation_manager"):
            await streaming_logger.log_progress(
                stage="context", message="Loading conversation context"
            )

            conversation = await container.conversation_manager.get_or_create_conversation(
                installation_id=task.installation_id,
                provider=task.provider,
                external_id=task.source_metadata.get("pr_number")
                    or task.source_metadata.get("issue_key")
                    or task.source_metadata.get("thread_ts")
                    or task_id,
            )

            context_data = await container.conversation_manager.get_context(
                conversation.id, limit=20
            )

            await container.conversation_manager.add_message(
                conversation_id=conversation.id,
                role="user",
                content=task.input_message,
            )
        else:
            context_data = None

        await streaming_logger.log_progress(
            stage="repository", message="Preparing repository"
        )

        repo_manager = RepoManager(base_path=Path("/tmp/repos"))
        repo_path = None

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
            stage="execution", message="Executing agent workflow"
        )

        agent_task = AgentTask(
            task_id=task_id,
            provider=task.provider,
            event_type=task.source_metadata.get("event_type", "unknown"),
            installation_id=task.installation_id,
            organization_id=task.source_metadata.get("organization_id", ""),
            input_message=task.input_message,
            source_metadata=task.source_metadata,
            priority=task.priority.value,
            created_at=task.created_at,
        )

        agent_context = AgentContext(
            task=agent_task,
            conversation_history=context_data.messages if context_data else [],
            repository_path=str(repo_path) if repo_path else None,
        )

        if hasattr(container, "brain_agent"):
            result = await container.brain_agent.process(agent_task, agent_context)
        else:
            cli_result = await container.cli_runner.execute_and_wait(
                command=["claude", "chat"],
                input_text=task.input_message,
                timeout_seconds=300,
            )
            result = type("Result", (), {
                "success": cli_result.success,
                "output": cli_result.output,
                "model_used": "claude-3-5-sonnet-20241022",
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "duration_seconds": 0.0,
                "error": cli_result.error,
            })()

        await streaming_logger.log_progress(
            stage="execution",
            message="Agent workflow completed",
            success=result.success,
        )

        if hasattr(container, "analytics") and result.success:
            await streaming_logger.log_progress(
                stage="analytics", message="Recording usage metrics"
            )

            await container.analytics.record_usage(
                task_id=task_id,
                installation_id=task.installation_id,
                provider=task.provider,
                model=result.model_used,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cost_usd=result.cost_usd,
                duration_seconds=result.duration_seconds,
            )

        if result.success:
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

                if posted and hasattr(container, "conversation_manager"):
                    await container.conversation_manager.add_message(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=result.output,
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
            error=result.error if hasattr(result, "error") else None,
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
