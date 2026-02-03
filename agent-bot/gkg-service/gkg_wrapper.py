import asyncio
import json
from pathlib import Path
import structlog

from config import settings

logger = structlog.get_logger()


class GKGWrapper:
    def __init__(self):
        self.gkg_binary = settings.gkg_binary
        self.data_dir = Path(settings.data_dir)
        self.repos_dir = Path(settings.repos_dir)
        self._ensure_directories()

    def _ensure_directories(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)

    async def _run_gkg_command(
        self, args: list[str], cwd: str | None = None
    ) -> tuple[str, str, int]:
        cmd = [self.gkg_binary] + args
        logger.debug("gkg_command", cmd=" ".join(cmd), cwd=cwd)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await process.communicate()
        return stdout.decode(), stderr.decode(), process.returncode or 0

    def _get_repo_path(self, org_id: str, repo: str) -> Path:
        return self.repos_dir / org_id / repo

    async def is_available(self) -> bool:
        try:
            stdout, _, code = await self._run_gkg_command(["--version"])
            return code == 0
        except FileNotFoundError:
            return False

    async def index_repo(self, org_id: str, repo_path: str) -> dict:
        logger.info("gkg_indexing_repo", org_id=org_id, repo_path=repo_path)

        output_dir = self.data_dir / org_id
        output_dir.mkdir(parents=True, exist_ok=True)

        stdout, stderr, code = await self._run_gkg_command(
            ["index", "--output", str(output_dir)],
            cwd=repo_path,
        )

        if code != 0:
            logger.error("gkg_index_failed", stderr=stderr)
            return {"success": False, "error": stderr}

        logger.info("gkg_index_completed", org_id=org_id)
        return {"success": True, "output": stdout}

    async def query_dependencies(
        self,
        org_id: str,
        repo: str,
        file_path: str,
        depth: int = 3,
    ) -> dict:
        db_path = self.data_dir / org_id

        if not db_path.exists():
            return {
                "dependencies": [],
                "formatted_output": "No index found for this organization",
            }

        query = f"""
        MATCH (f:File {{path: '{file_path}'}})-[:IMPORTS*1..{depth}]->(dep)
        RETURN dep.path as path, dep.type as type
        """

        stdout, stderr, code = await self._run_gkg_command(
            ["query", "--db", str(db_path), "--format", "json", query],
        )

        if code != 0:
            logger.error("gkg_query_failed", stderr=stderr)
            return {"dependencies": [], "formatted_output": f"Query failed: {stderr}"}

        try:
            results = json.loads(stdout) if stdout.strip() else []
        except json.JSONDecodeError:
            results = []

        formatted_lines = [f"Dependencies for {file_path}:"]
        for dep in results:
            formatted_lines.append(
                f"  - {dep.get('path', 'unknown')} ({dep.get('type', 'unknown')})"
            )

        return {
            "dependencies": results,
            "formatted_output": "\n".join(formatted_lines),
        }

    async def find_usages(
        self,
        org_id: str,
        symbol: str,
        repo: str = "*",
    ) -> list[dict]:
        db_path = self.data_dir / org_id

        if not db_path.exists():
            return []

        query = f"""
        MATCH (ref)-[:REFERENCES]->(s {{name: '{symbol}'}})
        RETURN ref.file as file, ref.line as line, ref.context as context
        """

        stdout, stderr, code = await self._run_gkg_command(
            ["query", "--db", str(db_path), "--format", "json", query],
        )

        if code != 0:
            logger.error("gkg_usage_query_failed", stderr=stderr)
            return []

        try:
            return json.loads(stdout) if stdout.strip() else []
        except json.JSONDecodeError:
            return []

    async def get_call_graph(
        self,
        org_id: str,
        repo: str,
        function_name: str,
        direction: str = "both",
        depth: int = 2,
    ) -> dict:
        db_path = self.data_dir / org_id

        if not db_path.exists():
            return {"callers": [], "callees": [], "formatted_graph": "No index found"}

        callers = []
        callees = []

        if direction in ("callers", "both"):
            query = f"""
            MATCH (caller:Function)-[:CALLS*1..{depth}]->(f:Function {{name: '{function_name}'}})
            RETURN caller.name as name, caller.file as file, caller.line as line
            """
            stdout, _, code = await self._run_gkg_command(
                ["query", "--db", str(db_path), "--format", "json", query],
            )
            if code == 0 and stdout.strip():
                try:
                    callers = json.loads(stdout)
                except json.JSONDecodeError:
                    pass

        if direction in ("callees", "both"):
            query = f"""
            MATCH (f:Function {{name: '{function_name}'}})-[:CALLS*1..{depth}]->(callee:Function)
            RETURN callee.name as name, callee.file as file, callee.line as line
            """
            stdout, _, code = await self._run_gkg_command(
                ["query", "--db", str(db_path), "--format", "json", query],
            )
            if code == 0 and stdout.strip():
                try:
                    callees = json.loads(stdout)
                except json.JSONDecodeError:
                    pass

        formatted_lines = [f"Call Graph for {function_name}:"]
        if callers:
            formatted_lines.append("\nCallers:")
            for c in callers:
                formatted_lines.append(
                    f"  <- {c.get('name', '?')} ({c.get('file', '?')}:{c.get('line', '?')})"
                )
        if callees:
            formatted_lines.append("\nCallees:")
            for c in callees:
                formatted_lines.append(
                    f"  -> {c.get('name', '?')} ({c.get('file', '?')}:{c.get('line', '?')})"
                )

        return {
            "callers": callers,
            "callees": callees,
            "formatted_graph": "\n".join(formatted_lines),
        }

    async def get_class_hierarchy(
        self,
        org_id: str,
        class_name: str,
        repo: str = "*",
    ) -> dict:
        db_path = self.data_dir / org_id

        if not db_path.exists():
            return {
                "parents": [],
                "children": [],
                "formatted_hierarchy": "No index found",
            }

        parents = []
        children = []

        parent_query = f"""
        MATCH (c:Class {{name: '{class_name}'}})-[:EXTENDS|IMPLEMENTS*1..5]->(parent)
        RETURN parent.name as name, parent.file as file
        """
        stdout, _, code = await self._run_gkg_command(
            ["query", "--db", str(db_path), "--format", "json", parent_query],
        )
        if code == 0 and stdout.strip():
            try:
                parents = json.loads(stdout)
            except json.JSONDecodeError:
                pass

        child_query = f"""
        MATCH (child)-[:EXTENDS|IMPLEMENTS*1..5]->(c:Class {{name: '{class_name}'}})
        RETURN child.name as name, child.file as file
        """
        stdout, _, code = await self._run_gkg_command(
            ["query", "--db", str(db_path), "--format", "json", child_query],
        )
        if code == 0 and stdout.strip():
            try:
                children = json.loads(stdout)
            except json.JSONDecodeError:
                pass

        formatted_lines = [f"Class Hierarchy for {class_name}:"]
        if parents:
            formatted_lines.append("\nParents (extends/implements):")
            for p in parents:
                formatted_lines.append(
                    f"  ^ {p.get('name', '?')} ({p.get('file', '?')})"
                )
        formatted_lines.append(f"\n  [{class_name}]")
        if children:
            formatted_lines.append("\nChildren (extended by):")
            for c in children:
                formatted_lines.append(
                    f"  v {c.get('name', '?')} ({c.get('file', '?')})"
                )

        return {
            "parents": parents,
            "children": children,
            "formatted_hierarchy": "\n".join(formatted_lines),
        }

    async def get_related_entities(
        self,
        org_id: str,
        entity: str,
        entity_type: str,
        relationship: str = "all",
    ) -> dict[str, list[dict]]:
        db_path = self.data_dir / org_id

        if not db_path.exists():
            return {}

        relationships: dict[str, list[dict]] = {}
        rel_types = (
            ["calls", "imports", "extends", "references"]
            if relationship == "all"
            else [relationship]
        )

        for rel in rel_types:
            query = f"""
            MATCH (e:{entity_type.capitalize()} {{name: '{entity}'}})-[:{rel.upper()}]->(related)
            RETURN related.name as name, related.file as file, related.line as line
            """
            stdout, _, code = await self._run_gkg_command(
                ["query", "--db", str(db_path), "--format", "json", query],
            )
            if code == 0 and stdout.strip():
                try:
                    relationships[rel] = json.loads(stdout)
                except json.JSONDecodeError:
                    relationships[rel] = []

        return relationships

    async def batch_related_entities(
        self,
        org_id: str,
        entities: list[dict[str, str]],
        depth: int = 1,
    ) -> dict[str, dict]:
        results = {}
        for entity in entities:
            name = entity.get("name", "")
            entity_type = entity.get("type", "function")
            if name:
                related = await self.get_related_entities(org_id, name, entity_type)
                results[name] = related
        return results

    async def get_indexed_repos_count(self, org_id: str | None = None) -> int:
        if org_id:
            org_path = self.data_dir / org_id
            if org_path.exists():
                return len(list(org_path.glob("*.db")))
            return 0

        count = 0
        for org_dir in self.data_dir.iterdir():
            if org_dir.is_dir():
                count += len(list(org_dir.glob("*.db")))
        return count
