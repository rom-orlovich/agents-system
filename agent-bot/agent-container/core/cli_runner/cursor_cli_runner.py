import asyncio
import subprocess
import json
import structlog
from pathlib import Path
from core.cli_runner.interface import CLIRunner, CLIResult

logger = structlog.get_logger()


class CursorCLIRunner:
    def __init__(self, cli_path: str = "cursor"):
        self.cli_path = cli_path

    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str],
    ) -> CLIResult:
        command = self._build_command(prompt, working_dir, model, agents)
        logger.info("cursor_cli_executing", command=" ".join(command))

        process_result = await self._run_command(command, working_dir)

        return self._parse_result(process_result)

    def _build_command(
        self, prompt: str, working_dir: str, model: str, agents: list[str]
    ) -> list[str]:
        command = [
            self.cli_path,
            "headless",
            "run",
            "--directory",
            working_dir,
            "--model",
            model,
            "--output-format",
            "json",
        ]

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
                returncode=process.returncode if process.returncode is not None else -1,
                stdout=stdout,
                stderr=stderr,
            )
        except Exception as e:
            logger.error("cursor_cli_execution_failed", error=str(e))
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout=b"",
                stderr=str(e).encode(),
            )

    def _parse_result(self, result: subprocess.CompletedProcess) -> CLIResult:
        if result.returncode != 0:
            error_message = result.stderr.decode() if result.stderr else "Unknown error"
            logger.error("cursor_cli_failed", error=error_message)
            return CLIResult(
                success=False,
                output="",
                error=error_message,
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0,
            )

        try:
            output = result.stdout.decode()
            json_output = json.loads(output)

            return CLIResult(
                success=True,
                output=json_output.get("output", output),
                error=None,
                cost_usd=json_output.get("metrics", {}).get("cost_usd", 0.0),
                input_tokens=json_output.get("metrics", {}).get("input_tokens", 0),
                output_tokens=json_output.get("metrics", {}).get("output_tokens", 0),
            )
        except json.JSONDecodeError:
            output = result.stdout.decode()
            logger.warning("cursor_cli_json_parse_failed", using_raw_output=True)
            return CLIResult(
                success=True,
                output=output,
                error=None,
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0,
            )
