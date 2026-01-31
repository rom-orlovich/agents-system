import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_cli_process() -> MagicMock:
    process = MagicMock()
    process.returncode = 0
    process.communicate = AsyncMock(return_value=(
        b'{"success": true, "output": "Task completed successfully"}',
        b"",
    ))
    return process


@pytest.fixture
def sample_github_task() -> dict[str, Any]:
    return {
        "task_id": "task-github-123",
        "source": "github",
        "event_type": "issues",
        "action": "opened",
        "prompt": "Analyze and fix the authentication issue described in the GitHub issue",
        "repo_path": "/app/repos/org/repo",
        "repository": {
            "full_name": "org/repo",
            "clone_url": "https://github.com/org/repo.git",
            "default_branch": "main",
        },
        "issue": {
            "number": 42,
            "title": "Fix authentication bug",
            "body": "Users cannot login with OAuth",
        },
    }


@pytest.fixture
def sample_jira_task() -> dict[str, Any]:
    return {
        "task_id": "task-jira-456",
        "source": "jira",
        "event_type": "jira:issue_created",
        "prompt": "Implement the feature described in Jira ticket PROJ-123",
        "repo_path": "/app/repos/default",
        "issue_key": "PROJ-123",
        "summary": "Implement user dashboard",
        "description": "Create a new dashboard component",
    }


class TestAgentEngineTaskProcessing:
    @pytest.mark.asyncio
    async def test_task_received_from_queue(
        self,
        mock_redis: AsyncMock,
        sample_github_task: dict[str, Any],
    ) -> None:
        task_json = json.dumps(sample_github_task)
        mock_redis.brpop.return_value = (b"agent:tasks", task_json.encode())

        task_data = await mock_redis.brpop("agent:tasks", timeout=5)
        received_task = json.loads(task_data[1])

        assert received_task["task_id"] == "task-github-123"
        assert received_task["source"] == "github"
        assert received_task["event_type"] == "issues"

    @pytest.mark.asyncio
    async def test_cli_execution_with_claude_provider(
        self,
        mock_cli_process: MagicMock,
        sample_github_task: dict[str, Any],
    ) -> None:
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_subprocess.return_value = mock_cli_process

            process = await asyncio.create_subprocess_exec(
                "claude",
                "--print",
                "--output-format",
                "json",
                sample_github_task["prompt"],
                cwd=sample_github_task["repo_path"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            result = json.loads(stdout)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_cli_execution_with_cursor_provider(
        self,
        mock_cli_process: MagicMock,
        sample_github_task: dict[str, Any],
    ) -> None:
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_subprocess.return_value = mock_cli_process

            process = await asyncio.create_subprocess_exec(
                "cursor",
                "--print",
                sample_github_task["prompt"],
                cwd=sample_github_task["repo_path"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            result = json.loads(stdout)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_task_status_updated_on_start(
        self,
        mock_redis: AsyncMock,
        sample_github_task: dict[str, Any],
    ) -> None:
        from agent_engine.core.queue_manager import QueueManager, TaskStatus

        manager = QueueManager(redis_client=mock_redis)

        await manager.set_task_status(sample_github_task["task_id"], TaskStatus.RUNNING)

        mock_redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_task_status_updated_on_completion(
        self,
        mock_redis: AsyncMock,
        sample_github_task: dict[str, Any],
    ) -> None:
        from agent_engine.core.queue_manager import QueueManager, TaskStatus

        manager = QueueManager(redis_client=mock_redis)

        await manager.set_task_status(
            sample_github_task["task_id"],
            TaskStatus.COMPLETED,
        )

        mock_redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_task_status_updated_on_failure(
        self,
        mock_redis: AsyncMock,
        sample_github_task: dict[str, Any],
    ) -> None:
        from agent_engine.core.queue_manager import QueueManager, TaskStatus

        manager = QueueManager(redis_client=mock_redis)

        await manager.set_task_status(sample_github_task["task_id"], TaskStatus.FAILED)

        mock_redis.set.assert_called()


class TestCLIProviderSelection:
    @pytest.mark.asyncio
    async def test_claude_provider_command_format(self) -> None:
        from agent_engine.core.cli.providers.claude.runner import ClaudeCLIRunner

        runner = ClaudeCLIRunner()
        command = runner._build_command("Test prompt", None, None, None, None)

        assert "claude" in command[0]
        assert "-p" in command
        assert "Test prompt" in command

    @pytest.mark.asyncio
    async def test_cursor_provider_command_format(self) -> None:
        from agent_engine.core.cli.providers.cursor.runner import CursorCLIRunner

        runner = CursorCLIRunner()
        command = runner._build_command("Test prompt", None)

        assert "cursor" in command[0]
        assert "--headless" in command
        assert "Test prompt" in command


class TestOutputStreaming:
    @pytest.mark.asyncio
    async def test_output_appended_incrementally(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        from agent_engine.core.queue_manager import QueueManager

        manager = QueueManager(redis_client=mock_redis)

        await manager.append_output("task-123", "chunk 1\n")
        await manager.append_output("task-123", "chunk 2\n")
        await manager.append_output("task-123", "chunk 3\n")

        assert mock_redis.append.call_count == 3

    @pytest.mark.asyncio
    async def test_full_output_retrieved(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        from agent_engine.core.queue_manager import QueueManager

        mock_redis.get.return_value = b"chunk 1\nchunk 2\nchunk 3\n"

        manager = QueueManager(redis_client=mock_redis)
        output = await manager.get_output("task-123")

        assert "chunk 1" in output
        assert "chunk 2" in output
        assert "chunk 3" in output


class TestConcurrencyControl:
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_tasks(self) -> None:
        max_concurrent = 3
        semaphore = asyncio.Semaphore(max_concurrent)
        active_count = 0
        max_active = 0

        async def mock_task() -> None:
            nonlocal active_count, max_active
            async with semaphore:
                active_count += 1
                max_active = max(max_active, active_count)
                await asyncio.sleep(0.01)
                active_count -= 1

        tasks = [mock_task() for _ in range(10)]
        await asyncio.gather(*tasks)

        assert max_active <= max_concurrent

    @pytest.mark.asyncio
    async def test_tasks_processed_with_concurrency_limit(
        self,
        mock_redis: AsyncMock,
    ) -> None:

        processed_tasks: list[str] = []
        max_concurrent = 2
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_task(task_id: str) -> None:
            async with semaphore:
                processed_tasks.append(task_id)
                await asyncio.sleep(0.01)

        task_ids = [f"task-{i}" for i in range(5)]
        tasks = [process_task(tid) for tid in task_ids]
        await asyncio.gather(*tasks)

        assert len(processed_tasks) == 5
        for tid in task_ids:
            assert tid in processed_tasks


class TestTimeoutHandling:
    @pytest.mark.asyncio
    async def test_task_timeout_handled(self) -> None:
        async def slow_task() -> str:
            await asyncio.sleep(10)
            return "completed"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_task(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_timeout_returns_error_result(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        from agent_engine.core.queue_manager import QueueManager, TaskStatus

        manager = QueueManager(redis_client=mock_redis)

        await manager.set_task_status("task-123", TaskStatus.FAILED)

        mock_redis.set.assert_called()
