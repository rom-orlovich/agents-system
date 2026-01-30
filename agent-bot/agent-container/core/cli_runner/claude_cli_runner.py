import asyncio
import subprocess
from pathlib import Path
import structlog
from core.cli_runner.interface import CLIResult
from core.streaming_logger import StreamingLogger

logger = structlog.get_logger()


class ClaudeCLIRunner:
    def __init__(
        self, cli_path: str = "claude", streaming_logger: StreamingLogger | None = None
    ):
        self.cli_path = cli_path
        self.streaming_logger = streaming_logger

    async def execute(
        self,
        prompt: str,
        working_dir: str,
        model: str,
        agents: list[str],
        streaming_logger: StreamingLogger | None = None,
    ) -> CLIResult:
        command = self._build_command(prompt, working_dir, model, agents)
        logger_to_use = streaming_logger or self.streaming_logger
        process_result = await self._run_command(command, working_dir, logger_to_use)
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
        self,
        command: list[str],
        working_dir: str,
        streaming_logger: StreamingLogger | None,
    ) -> subprocess.CompletedProcess:
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            async def stream_output(
                stream: asyncio.StreamReader, stream_name: str
            ) -> list[str]:
                lines: list[str] = []
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded_line = line.decode().rstrip()
                    lines.append(decoded_line)
                    if streaming_logger:
                        await streaming_logger.log_cli_output(
                            decoded_line, stream=stream_name
                        )
                return lines

            stdout_lines, stderr_lines = await asyncio.gather(
                stream_output(process.stdout, "stdout"),
                stream_output(process.stderr, "stderr"),
            )

            await process.wait()

            stdout_bytes = "\n".join(stdout_lines).encode() if stdout_lines else b""
            stderr_bytes = "\n".join(stderr_lines).encode() if stderr_lines else b""

            return subprocess.CompletedProcess(
                args=command,
                returncode=process.returncode if process.returncode else 0,
                stdout=stdout_bytes,
                stderr=stderr_bytes,
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
