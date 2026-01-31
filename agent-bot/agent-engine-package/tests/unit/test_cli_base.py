import pytest
from agent_engine.core.cli.base import CLIResult, CLIProvider


class TestCLIResult:
    def test_cli_result_immutable(self) -> None:
        result = CLIResult(
            success=True,
            output="test",
            clean_output="test",
            cost_usd=0.01,
            input_tokens=100,
            output_tokens=50,
            error=None,
        )
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore

    def test_cli_result_fields(self) -> None:
        result = CLIResult(
            success=True,
            output="full output",
            clean_output="clean",
            cost_usd=0.0123,
            input_tokens=100,
            output_tokens=50,
            error=None,
        )
        assert result.success is True
        assert result.output == "full output"
        assert result.clean_output == "clean"
        assert result.cost_usd == 0.0123
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.error is None

    def test_cli_result_with_error(self) -> None:
        result = CLIResult(
            success=False,
            output="",
            clean_output="",
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            error="Test error message",
        )
        assert result.success is False
        assert result.error == "Test error message"

    def test_cli_provider_protocol(self) -> None:
        assert hasattr(CLIProvider, "run")
