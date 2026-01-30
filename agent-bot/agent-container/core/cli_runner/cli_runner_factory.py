import os
from core.cli_runner.interface import CLIRunner
from core.cli_runner.claude_cli_runner import ClaudeCLIRunner
from core.cli_runner.cursor_cli_runner import CursorCLIRunner


class CLIRunnerFactory:
    @staticmethod
    def create(runner_type: str | None = None) -> CLIRunner:
        if runner_type is None:
            runner_type = os.getenv("CLI_RUNNER_TYPE", "claude")

        runner_type = runner_type.lower()

        if runner_type == "claude":
            return ClaudeCLIRunner()
        elif runner_type == "cursor":
            return CursorCLIRunner()
        else:
            raise ValueError(f"Unknown CLI runner type: {runner_type}")
