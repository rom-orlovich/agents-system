import pytest
from core.cli_runner.cursor_cli_runner import CursorCLIRunner
from core.cli_runner.interface import CLIResult
import subprocess


@pytest.fixture
def cursor_runner():
    return CursorCLIRunner(cli_path="cursor")


def test_cursor_cli_runner_builds_correct_command(cursor_runner: CursorCLIRunner):
    command = cursor_runner._build_command(
        prompt="analyze this code",
        working_dir="/app/tmp",
        model="gpt-4",
        agents=["planning", "coding"],
    )

    assert "cursor" in command
    assert "headless" in command
    assert "run" in command
    assert "--directory" in command
    assert "/app/tmp" in command
    assert "--model" in command
    assert "gpt-4" in command
    assert "--output-format" in command
    assert "json" in command
    assert "--agents" in command
    assert "planning,coding" in command
    assert "analyze this code" in command


def test_cursor_cli_runner_parses_success_result(cursor_runner: CursorCLIRunner):
    mock_result = subprocess.CompletedProcess(
        args=["cursor", "headless", "run"],
        returncode=0,
        stdout=b'{"output": "Task completed", "metrics": {"cost_usd": 0.05, "input_tokens": 100, "output_tokens": 200}}',
        stderr=b"",
    )

    cli_result = cursor_runner._parse_result(mock_result)

    assert cli_result.success is True
    assert cli_result.output == "Task completed"
    assert cli_result.cost_usd == 0.05
    assert cli_result.input_tokens == 100
    assert cli_result.output_tokens == 200
    assert cli_result.error is None


def test_cursor_cli_runner_parses_failure_result(cursor_runner: CursorCLIRunner):
    mock_result = subprocess.CompletedProcess(
        args=["cursor", "headless", "run"],
        returncode=1,
        stdout=b"",
        stderr=b"Error: Command failed",
    )

    cli_result = cursor_runner._parse_result(mock_result)

    assert cli_result.success is False
    assert cli_result.error == "Error: Command failed"
    assert cli_result.cost_usd == 0.0


def test_cursor_cli_runner_handles_non_json_output(cursor_runner: CursorCLIRunner):
    mock_result = subprocess.CompletedProcess(
        args=["cursor", "headless", "run"],
        returncode=0,
        stdout=b"Plain text output without JSON",
        stderr=b"",
    )

    cli_result = cursor_runner._parse_result(mock_result)

    assert cli_result.success is True
    assert cli_result.output == "Plain text output without JSON"
    assert cli_result.cost_usd == 0.0
