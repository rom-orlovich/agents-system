import asyncio
import subprocess
from typing import Any

from .base import BaseSkill, SkillInput, SkillOutput, SkillType


class DiscoverySkill(BaseSkill):
    skill_type = SkillType.DISCOVERY

    def get_available_actions(self) -> list[str]:
        return [
            "search_files",
            "search_code",
            "list_directory",
            "get_file_info",
            "find_references",
            "get_project_structure",
        ]

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        action = skill_input.action
        params = skill_input.parameters
        context = skill_input.context

        try:
            working_dir = context.get("working_dir", "/app/repos/default")

            if action == "search_files":
                result = await self._search_files(working_dir, params["pattern"])
            elif action == "search_code":
                result = await self._search_code(working_dir, params["query"])
            elif action == "list_directory":
                result = await self._list_directory(working_dir, params.get("path", "."))
            elif action == "get_file_info":
                result = await self._get_file_info(working_dir, params["path"])
            elif action == "find_references":
                result = await self._find_references(working_dir, params["symbol"])
            elif action == "get_project_structure":
                result = await self._get_project_structure(working_dir)
            else:
                return SkillOutput(success=False, result=None, error=f"Unknown action: {action}")

            return SkillOutput(success=True, result=result)
        except Exception as e:
            self._logger.exception("discovery_failed", action=action)
            return SkillOutput(success=False, result=None, error=str(e))

    async def _search_files(self, working_dir: str, pattern: str) -> dict[str, Any]:
        cmd = f"find {working_dir} -name '{pattern}' -type f | head -100"
        result = await self._run_command(cmd)
        files = result.strip().split("\n") if result.strip() else []
        return {"files": files, "count": len(files)}

    async def _search_code(self, working_dir: str, query: str) -> dict[str, Any]:
        cmd = f"grep -rn '{query}' {working_dir} --include='*.py' | head -50"
        result = await self._run_command(cmd)
        matches = result.strip().split("\n") if result.strip() else []
        return {"matches": matches, "count": len(matches)}

    async def _list_directory(self, working_dir: str, path: str) -> dict[str, Any]:
        full_path = f"{working_dir}/{path}" if path != "." else working_dir
        cmd = f"ls -la {full_path}"
        result = await self._run_command(cmd)
        return {"listing": result, "path": full_path}

    async def _get_file_info(self, working_dir: str, path: str) -> dict[str, Any]:
        full_path = f"{working_dir}/{path}"
        stat_cmd = f"stat {full_path}"
        wc_cmd = f"wc -l {full_path}"
        stat_result = await self._run_command(stat_cmd)
        wc_result = await self._run_command(wc_cmd)
        return {"stat": stat_result, "lines": wc_result.split()[0] if wc_result else "0"}

    async def _find_references(self, working_dir: str, symbol: str) -> dict[str, Any]:
        cmd = f"grep -rn '\\b{symbol}\\b' {working_dir} --include='*.py' | head -50"
        result = await self._run_command(cmd)
        refs = result.strip().split("\n") if result.strip() else []
        return {"references": refs, "count": len(refs)}

    async def _get_project_structure(self, working_dir: str) -> dict[str, Any]:
        cmd = f"find {working_dir} -type f -name '*.py' | head -100"
        result = await self._run_command(cmd)
        files = result.strip().split("\n") if result.strip() else []
        return {"files": files, "count": len(files)}

    async def _run_command(self, cmd: str) -> str:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode("utf-8")
