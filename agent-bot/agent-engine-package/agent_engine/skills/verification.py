from typing import Any
import subprocess
import asyncio

from .base import BaseSkill, SkillInput, SkillOutput, SkillType


class VerificationSkill(BaseSkill):
    skill_type = SkillType.VERIFICATION

    def get_available_actions(self) -> list[str]:
        return [
            "verify_tests",
            "verify_lint",
            "verify_types",
            "verify_file_sizes",
            "verify_no_secrets",
            "verify_all",
        ]

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        action = skill_input.action
        params = skill_input.parameters
        context = skill_input.context

        try:
            working_dir = context.get("working_dir", "/app/repos/default")

            if action == "verify_tests":
                result = await self._verify_tests(working_dir)
            elif action == "verify_lint":
                result = await self._verify_lint(working_dir)
            elif action == "verify_types":
                result = await self._verify_types(working_dir)
            elif action == "verify_file_sizes":
                result = await self._verify_file_sizes(working_dir)
            elif action == "verify_no_secrets":
                result = await self._verify_no_secrets(working_dir)
            elif action == "verify_all":
                result = await self._verify_all(working_dir)
            else:
                return SkillOutput(success=False, result=None, error=f"Unknown action: {action}")

            return SkillOutput(success=True, result=result)
        except Exception as e:
            self._logger.exception("verification_failed", action=action)
            return SkillOutput(success=False, result=None, error=str(e))

    async def _verify_tests(self, working_dir: str) -> dict[str, Any]:
        cmd = f"cd {working_dir} && pytest -v --tb=short 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {"passed": exit_code == 0, "output": output}

    async def _verify_lint(self, working_dir: str) -> dict[str, Any]:
        cmd = f"cd {working_dir} && ruff check . 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {"passed": exit_code == 0, "output": output}

    async def _verify_types(self, working_dir: str) -> dict[str, Any]:
        cmd = f"cd {working_dir} && mypy . --ignore-missing-imports 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {"passed": exit_code == 0, "output": output}

    async def _verify_file_sizes(self, working_dir: str) -> dict[str, Any]:
        cmd = f"find {working_dir} -name '*.py' -exec wc -l {{}} \\; | awk '$1 > 300 {{print}}'"
        output = await self._run_command(cmd)
        oversized = output.strip().split("\n") if output.strip() else []
        return {"passed": len(oversized) == 0, "oversized_files": oversized}

    async def _verify_no_secrets(self, working_dir: str) -> dict[str, Any]:
        patterns = ["password=", "api_key=", "secret=", "token="]
        issues = []
        for pattern in patterns:
            cmd = f"grep -rn '{pattern}' {working_dir} --include='*.py' | grep -v '.env' | head -10"
            output = await self._run_command(cmd)
            if output.strip():
                issues.extend(output.strip().split("\n"))
        return {"passed": len(issues) == 0, "potential_secrets": issues}

    async def _verify_all(self, working_dir: str) -> dict[str, Any]:
        results = {
            "tests": await self._verify_tests(working_dir),
            "lint": await self._verify_lint(working_dir),
            "types": await self._verify_types(working_dir),
            "file_sizes": await self._verify_file_sizes(working_dir),
            "secrets": await self._verify_no_secrets(working_dir),
        }
        all_passed = all(r.get("passed", False) for r in results.values())
        return {"all_passed": all_passed, "details": results}

    async def _run_command(self, cmd: str) -> str:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return stdout.decode("utf-8")

    async def _run_command_with_code(self, cmd: str) -> tuple[str, int]:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        return stdout.decode("utf-8"), proc.returncode or 0
