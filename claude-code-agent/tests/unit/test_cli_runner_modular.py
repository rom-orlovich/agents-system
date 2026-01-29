import pytest
import asyncio
from pathlib import Path
from typing import Protocol, runtime_checkable
from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock
import tempfile
import shutil


@pytest.fixture
def temp_working_dir():
    """Create a temporary working directory for CLI tests."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@dataclass
class CLIResult:
    success: bool
    output: str
    clean_output: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    error: str | None = None


@runtime_checkable
class CLIRunner(Protocol):
    async def run(
        self,
        prompt: str,
        working_dir: Path,
        output_queue: asyncio.Queue,
        task_id: str = "",
        timeout_seconds: int = 3600,
        model: str | None = None,
        allowed_tools: str | None = None,
        agents: str | None = None,
        debug_mode: str | None = None,
    ) -> CLIResult:
        ...


class TestCLIRunnerProtocol:
    @pytest.mark.asyncio
    async def test_protocol_definition(self):
        from core.cli.base import CLIRunner as BaseCLIRunner

        assert hasattr(BaseCLIRunner, "run")

    @pytest.mark.asyncio
    async def test_protocol_accepts_implementations(self):
        from core.cli.base import CLIRunner as BaseCLIRunner

        class MockCLIRunner:
            async def run(
                self,
                prompt: str,
                working_dir: Path,
                output_queue: asyncio.Queue,
                task_id: str = "",
                timeout_seconds: int = 3600,
                model: str | None = None,
                allowed_tools: str | None = None,
                agents: str | None = None,
                debug_mode: str | None = None,
            ) -> CLIResult:
                return CLIResult(
                    success=True,
                    output="test",
                    clean_output="test",
                    cost_usd=0.01,
                    input_tokens=10,
                    output_tokens=20,
                )

        mock_runner = MockCLIRunner()
        assert isinstance(mock_runner, BaseCLIRunner)


class TestClaudeCLIRunner:
    @pytest.mark.asyncio
    async def test_claude_runner_implements_protocol(self):
        from core.cli.claude import ClaudeCLIRunner
        from core.cli.base import CLIRunner

        runner = ClaudeCLIRunner()
        assert isinstance(runner, CLIRunner)

    @pytest.mark.asyncio
    async def test_claude_runner_returns_cli_result(self, temp_working_dir):
        from core.cli.claude import ClaudeCLIRunner
        from core.cli.base import CLIResult

        runner = ClaudeCLIRunner()
        queue = asyncio.Queue()

        result = await runner.run(
            prompt="test prompt",
            working_dir=temp_working_dir,
            output_queue=queue,
            task_id="test-123",
        )

        assert isinstance(result, CLIResult)
        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "clean_output")
        assert hasattr(result, "cost_usd")
        assert hasattr(result, "input_tokens")
        assert hasattr(result, "output_tokens")
        assert hasattr(result, "error")

    @pytest.mark.asyncio
    async def test_claude_runner_handles_subprocess_creation(self, temp_working_dir):
        from core.cli.claude import ClaudeCLIRunner

        runner = ClaudeCLIRunner()
        queue = asyncio.Queue()

        result = await runner.run(
            prompt="echo test",
            working_dir=temp_working_dir,
            output_queue=queue,
            task_id="test-subprocess",
            timeout_seconds=10,
        )

        assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_claude_runner_supports_model_parameter(self, temp_working_dir):
        from core.cli.claude import ClaudeCLIRunner
        from core.cli.base import CLIResult

        runner = ClaudeCLIRunner()
        queue = asyncio.Queue()

        result = await runner.run(
            prompt="test",
            working_dir=temp_working_dir,
            output_queue=queue,
            model="opus",
        )

        assert isinstance(result, CLIResult)

    @pytest.mark.asyncio
    async def test_claude_runner_supports_allowed_tools(self, temp_working_dir):
        from core.cli.claude import ClaudeCLIRunner
        from core.cli.base import CLIResult

        runner = ClaudeCLIRunner()
        queue = asyncio.Queue()

        result = await runner.run(
            prompt="test",
            working_dir=temp_working_dir,
            output_queue=queue,
            allowed_tools="Read,Edit",
        )

        assert isinstance(result, CLIResult)

    @pytest.mark.asyncio
    async def test_claude_runner_supports_agents_parameter(self, temp_working_dir):
        from core.cli.claude import ClaudeCLIRunner
        from core.cli.base import CLIResult

        runner = ClaudeCLIRunner()
        queue = asyncio.Queue()

        agents_config = '{"test": {"description": "test agent"}}'
        result = await runner.run(
            prompt="test",
            working_dir=temp_working_dir,
            output_queue=queue,
            agents=agents_config,
        )

        assert isinstance(result, CLIResult)


class TestCLIRunnerSwitching:
    @pytest.mark.asyncio
    async def test_can_switch_cli_implementations(self):
        from core.cli.base import CLIRunner, CLIResult

        class CustomCLIRunner:
            async def run(
                self,
                prompt: str,
                working_dir: Path,
                output_queue: asyncio.Queue,
                task_id: str = "",
                timeout_seconds: int = 3600,
                model: str | None = None,
                allowed_tools: str | None = None,
                agents: str | None = None,
                debug_mode: str | None = None,
            ) -> CLIResult:
                return CLIResult(
                    success=True,
                    output="custom output",
                    clean_output="custom clean",
                    cost_usd=0.05,
                    input_tokens=50,
                    output_tokens=100,
                )

        runner = CustomCLIRunner()
        assert isinstance(runner, CLIRunner)

        queue = asyncio.Queue()
        result = await runner.run(
            prompt="test",
            working_dir=Path("/tmp"),
            output_queue=queue,
        )

        assert result.output == "custom output"
        assert result.cost_usd == 0.05

    @pytest.mark.asyncio
    async def test_cli_runner_factory_pattern(self):
        from core.cli.base import CLIRunner, CLIResult

        def get_cli_runner(runner_type: str) -> CLIRunner:
            if runner_type == "mock":

                class MockRunner:
                    async def run(self, *args, **kwargs) -> CLIResult:
                        return CLIResult(
                            success=True,
                            output="mock",
                            clean_output="mock",
                            cost_usd=0.0,
                            input_tokens=0,
                            output_tokens=0,
                        )

                return MockRunner()
            else:
                from core.cli.claude import ClaudeCLIRunner

                return ClaudeCLIRunner()

        mock_runner = get_cli_runner("mock")
        assert isinstance(mock_runner, CLIRunner)

        claude_runner = get_cli_runner("claude")
        assert isinstance(claude_runner, CLIRunner)


class TestCLIResultDataclass:
    def test_cli_result_creation(self):
        from core.cli.base import CLIResult

        result = CLIResult(
            success=True,
            output="test output",
            clean_output="clean output",
            cost_usd=0.01,
            input_tokens=10,
            output_tokens=20,
        )

        assert result.success is True
        assert result.output == "test output"
        assert result.clean_output == "clean output"
        assert result.cost_usd == 0.01
        assert result.input_tokens == 10
        assert result.output_tokens == 20
        assert result.error is None

    def test_cli_result_with_error(self):
        from core.cli.base import CLIResult

        result = CLIResult(
            success=False,
            output="",
            clean_output="",
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            error="Process failed",
        )

        assert result.success is False
        assert result.error == "Process failed"
