from typing import Any
import subprocess
import asyncio

from .base import BaseSkill, SkillInput, SkillOutput, SkillType


class CodeRefactoringSkill(BaseSkill):
    skill_type = SkillType.CODE_REFACTORING

    def get_available_actions(self) -> list[str]:
        return [
            "rename_symbol",
            "extract_function",
            "split_file",
            "organize_imports",
            "format_code",
        ]

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        action = skill_input.action
        params = skill_input.parameters
        context = skill_input.context

        try:
            working_dir = context.get("working_dir", "/app/repos/default")

            if action == "rename_symbol":
                result = await self._rename_symbol(
                    working_dir, params["old_name"], params["new_name"]
                )
            elif action == "extract_function":
                result = await self._extract_function(
                    working_dir, params["file"], params["start_line"], params["end_line"]
                )
            elif action == "split_file":
                result = await self._split_file(working_dir, params["file"])
            elif action == "organize_imports":
                result = await self._organize_imports(working_dir)
            elif action == "format_code":
                result = await self._format_code(working_dir)
            else:
                return SkillOutput(success=False, result=None, error=f"Unknown action: {action}")

            return SkillOutput(success=True, result=result)
        except Exception as e:
            self._logger.exception("refactoring_failed", action=action)
            return SkillOutput(success=False, result=None, error=str(e))

    async def _rename_symbol(
        self, working_dir: str, old_name: str, new_name: str
    ) -> dict[str, Any]:
        cmd = f"cd {working_dir} && find . -name '*.py' -exec sed -i 's/\\b{old_name}\\b/{new_name}/g' {{}} \\;"
        await self._run_command(cmd)
        verify_cmd = f"grep -rn '\\b{new_name}\\b' {working_dir} --include='*.py' | wc -l"
        count = await self._run_command(verify_cmd)
        return {
            "old_name": old_name,
            "new_name": new_name,
            "occurrences_updated": count.strip(),
        }

    async def _extract_function(
        self, working_dir: str, file: str, start_line: int, end_line: int
    ) -> dict[str, Any]:
        return {
            "message": "Function extraction requires manual review",
            "file": file,
            "lines": f"{start_line}-{end_line}",
            "action": "Review the specified lines and extract to a new function",
        }

    async def _split_file(self, working_dir: str, file: str) -> dict[str, Any]:
        full_path = f"{working_dir}/{file}"
        wc_cmd = f"wc -l {full_path}"
        wc_result = await self._run_command(wc_cmd)
        line_count = int(wc_result.split()[0]) if wc_result.strip() else 0

        if line_count <= 300:
            return {"message": f"File has {line_count} lines, no split needed"}

        return {
            "message": f"File has {line_count} lines, consider splitting",
            "file": file,
            "suggested_modules": [
                f"{file.replace('.py', '')}_constants.py",
                f"{file.replace('.py', '')}_models.py",
                f"{file.replace('.py', '')}_core.py",
            ],
        }

    async def _organize_imports(self, working_dir: str) -> dict[str, Any]:
        cmd = f"cd {working_dir} && ruff check --select I --fix . 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {"success": exit_code == 0, "output": output}

    async def _format_code(self, working_dir: str) -> dict[str, Any]:
        cmd = f"cd {working_dir} && ruff format . 2>&1"
        output, exit_code = await self._run_command_with_code(cmd)
        return {"success": exit_code == 0, "output": output}

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
