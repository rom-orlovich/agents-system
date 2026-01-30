import asyncio
import redis.asyncio as redis
import structlog
import os
from pathlib import Path
from core.task_logger import TaskLogger
from core.streaming_logger import StreamingLogger
from core.result_poster import ResultPoster, WebhookProvider
from core.mcp_client import MCPClient
from core.cli_runner.claude_cli_runner import ClaudeCLIRunner
from core.types import MCPClientProtocol
import json

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
worker_id = f"worker-{os.getpid()}"


async def process_task(task_data: dict, mcp_client: MCPClientProtocol) -> None:
    task_id = task_data.get("task_id", "unknown")
    task_logger = TaskLogger.get_or_create(task_id)
    streaming_logger = StreamingLogger(task_id)

    await streaming_logger.log_progress(
        stage="initialization", message="Task received by agent"
    )

    task_logger.log_agent_output("task_started", status="running")

    cli_runner = ClaudeCLIRunner()

    try:
        await streaming_logger.log_progress(
            stage="execution", message="Starting CLI execution"
        )

        result = await cli_runner.execute(
            prompt=task_data.get("input_message", ""),
            working_dir="/app/tmp",
            model=task_data.get("model", "claude-3-opus"),
            agents=[],
        )

        await streaming_logger.log_progress(
            stage="execution", message="CLI execution completed", success=result.success
        )

        task_logger.log_agent_output(
            "task_completed", success=result.success, output=result.output
        )

        task_logger.write_final_result(
            {
                "success": result.success,
                "result": result.output,
                "error": result.error,
                "metrics": {
                    "cost_usd": result.cost_usd,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                },
            }
        )

        provider_str = task_data.get("source_metadata", {}).get("provider")
        if provider_str and result.success:
            await streaming_logger.log_progress(
                stage="posting_result", message=f"Posting result to {provider_str}"
            )

            try:
                provider = WebhookProvider(provider_str)
                result_poster = ResultPoster(mcp_client)

                posted = await result_poster.post_result(
                    provider=provider,
                    metadata=task_data.get("source_metadata", {}),
                    result=result.output,
                )

                if posted:
                    await streaming_logger.log_progress(
                        stage="posting_result",
                        message=f"Successfully posted result to {provider_str}",
                        success=True,
                    )
                else:
                    await streaming_logger.log_error(
                        error=f"Failed to post result to {provider_str}"
                    )
            except Exception as e:
                logger.error("result_posting_error", task_id=task_id, error=str(e))
                await streaming_logger.log_error(
                    error=f"Result posting failed: {str(e)}"
                )

        await streaming_logger.log_completion(
            success=result.success, result=result.output, error=result.error
        )

    except Exception as e:
        logger.error("task_processing_failed", task_id=task_id, error=str(e))
        task_logger.log_agent_output("task_failed", error=str(e))
        await streaming_logger.log_error(error=str(e))
        await streaming_logger.log_completion(success=False, error=str(e))


async def main():
    redis_client = await redis.from_url(
        redis_url, encoding="utf-8", decode_responses=True
    )

    mcp_client = MCPClient()

    logger.info("task_worker_started", worker_id=worker_id)

    while True:
        try:
            result = await redis_client.bzpopmin("tasks", timeout=5)

            if result:
                queue_name, task_data_str, score = result
                task_data = json.loads(task_data_str)

                logger.info(
                    "task_dequeued",
                    task_id=task_data.get("task_id"),
                    worker_id=worker_id,
                )

                await process_task(task_data, mcp_client)
        except Exception as e:
            logger.error("worker_error", error=str(e))
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
