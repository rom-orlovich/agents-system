import asyncio
import subprocess
from pathlib import Path
import structlog
from core.cli_runner.interface import CLIResult

logger = structlog.get_logger()


class ClaudeCLIRunner:
    def __init__(self, cli_path: str = "claude"):
        self.cli_path = cli_path

    async def execute(
        self, prompt: str, working_dir: str, model: str, agents: list[str]
    ) -> CLIResult:
        command = self._build_command(prompt, working_dir, model, agents)
        process_result = await self._run_command(command, working_dir)
        return self._parse_result(process_result)

    def _build_command(
        self, prompt: str, working_dir: str, model: str, agents: list[str]
    ) -> list[str]:
        command = [self.cli_path, "run"]
        command.extend(["--model", model])
        if agents:
            command.extend(["--agents", ",".join(agents)])
        command.append(prompt)
        return command

    async def _run_command(
        self, command: list[str], working_dir: str
    ) -> subprocess.CompletedProcess:
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            return subprocess.CompletedProcess(
                args=command,
                returncode=process.returncode if process.returncode else 0,
                stdout=stdout,
                stderr=stderr,
            )
        except Exception as e:
            logger.error("cli_execution_failed", error=str(e))
            return subprocess.CompletedProcess(
                args=command, returncode=1, stdout=b"", stderr=str(e).encode()
            )

    def _parse_result(self, result: subprocess.CompletedProcess) -> CLIResult:
        if result.returncode != 0:
            return CLIResult(
                success=False,
                output="",
                error=result.stderr.decode() if result.stderr else "Unknown error",
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0,
            )

        output = result.stdout.decode() if result.stdout else ""

        return CLIResult(
            success=True,
            output=output,
            error=None,
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
        )
