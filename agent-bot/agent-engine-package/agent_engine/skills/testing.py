from typing import Any
import subprocess
import asyncio

from .base import BaseSkill, SkillInput, SkillOutput, SkillType


class TestingSkill(BaseSkill):
    skill_type = SkillType.TESTING

    def get_available_actions(self) -> list[str]:
        return [
            "run_all_tests",
            "run_test_file",
            "run_test_function",
            "get_coverage",
            "run_linting",
            "run_type_check",
        ]

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        action = skill_input.action
        params = skill_input.parameters
        context = skill_input.context

        try:
            working_dir = context.get("working_dir", "/app/repos/default")

            if action == "run_all_tests":
                result = await self._run_all_tests(working_dir)
            elif action == "run_test_file":
                result = await self._run_test_file(working_dir, params["file"])
            elif action == "run_test_function":
                result = await self._run_test_function(
                    working_dir, params["file"], params["function"]
                )
            elif action == "get_coverage":
                result = await self._get_coverage(working_dir)
            elif action == "run_linting":
                result = await self._run_linting(working_dir)
            elif action == "run_type_check":
                result = await self._run_type_check(working_dir)
            else:
                return SkillOutput(success=False, result=None, error=f"Unknown action: {action}")

            return SkillOutput(success=True, result=result)
        except Exception as e:
            self._logger.exception("testing_failed", action=action)
            return SkillOutput(success=False, result=None, error=str(e))

    async def _run_all_tests(self, working_dir: str) -> dict[str, Any]:
        cmd = f"cd {working_dir} && pytest -v --tb=short 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {
            "output": output,
            "passed": exit_code == 0,
            "exit_code": exit_code,
        }

    async def _run_test_file(self, working_dir: str, file: str) -> dict[str, Any]:
        cmd = f"cd {working_dir} && pytest {file} -v --tb=short 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {
            "output": output,
            "passed": exit_code == 0,
            "file": file,
        }

    async def _run_test_function(
        self, working_dir: str, file: str, function: str
    ) -> dict[str, Any]:
        cmd = f"cd {working_dir} && pytest {file}::{function} -v --tb=short 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {
            "output": output,
            "passed": exit_code == 0,
            "function": function,
        }

    async def _get_coverage(self, working_dir: str) -> dict[str, Any]:
        cmd = f"cd {working_dir} && pytest --cov=. --cov-report=term-missing 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {"output": output, "exit_code": exit_code}

    async def _run_linting(self, working_dir: str) -> dict[str, Any]:
        cmd = f"cd {working_dir} && ruff check . 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {
            "output": output,
            "passed": exit_code == 0,
            "tool": "ruff",
        }

    async def _run_type_check(self, working_dir: str) -> dict[str, Any]:
        cmd = f"cd {working_dir} && mypy . --ignore-missing-imports 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {
            "output": output,
            "passed": exit_code == 0,
            "tool": "mypy",
        }

    async def _run_command_with_code(self, cmd: str) -> tuple[str, int]:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode("utf-8"), proc.returncode or 0
