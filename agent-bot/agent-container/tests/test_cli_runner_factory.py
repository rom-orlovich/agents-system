import pytest
import os
from core.cli_runner.cli_runner_factory import CLIRunnerFactory
from core.cli_runner.claude_cli_runner import ClaudeCLIRunner
from core.cli_runner.cursor_cli_runner import CursorCLIRunner


def test_factory_creates_claude_runner_by_default():
    runner = CLIRunnerFactory.create("claude")
    assert isinstance(runner, ClaudeCLIRunner)


def test_factory_creates_cursor_runner():
    runner = CLIRunnerFactory.create("cursor")
    assert isinstance(runner, CursorCLIRunner)


def test_factory_raises_error_for_unknown_type():
    with pytest.raises(ValueError, match="Unknown CLI runner type"):
        CLIRunnerFactory.create("unknown")


def test_factory_uses_environment_variable(monkeypatch):
    monkeypatch.setenv("CLI_RUNNER_TYPE", "cursor")
    runner = CLIRunnerFactory.create()
    assert isinstance(runner, CursorCLIRunner)
