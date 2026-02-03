import asyncio
import json
from pathlib import Path
import structlog

from core.models import (
    DependencyResult,
    DependencyItem,
    UsageResult,
    CallGraphResult,
    CallGraphNode,
    HierarchyResult,
    HierarchyNode,
    RelatedEntitiesResult,
    RelatedEntity,
)

logger = structlog.get_logger()


class GKGBinaryAdapter:
    """Adapter for GKG CLI binary."""

    def __init__(
        self,
        binary_path: str = "gkg",
        data_dir: str = "/data/gkg",
        repos_dir: str = "/data/repos",
    ):
        self._binary = binary_path
        self._data_dir = Path(data_dir)
        self._repos_dir = Path(repos_dir)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._repos_dir.mkdir(parents=True, exist_ok=True)

    async def _run_command(
        self,
        args: list[str],
        cwd: str | None = None,
    ) -> tuple[str, str, int]:
        cmd = [self._binary] + args
        logger.debug("gkg_command", cmd=" ".join(cmd), cwd=cwd)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await process.communicate()
        return stdout.decode(), stderr.decode(), process.returncode or 0

    def _get_db_path(self, org_id: str) -> Path:
        return self._data_dir / org_id

    async def is_available(self) -> bool:
        try:
            _, _, code = await self._run_command(["--version"])
            return code == 0
        except FileNotFoundError:
            return False

    async def query_dependencies(
        self,
        org_id: str,
        repo: str,
        file_path: str,
        depth: int,
    ) -> DependencyResult:
        db_path = self._get_db_path(org_id)

        if not db_path.exists():
            return DependencyResult(
                file_path=file_path,
                repo=repo,
                dependencies=[],
                formatted_output="No index found for this organization",
            )

        query = f"""
        MATCH (f:File {{path: '{file_path}'}})-[:IMPORTS*1..{depth}]->(dep)
        RETURN dep.path as path, dep.type as type
        """

        stdout, stderr, code = await self._run_command(
            ["query", "--db", str(db_path), "--format", "json", query],
        )

        if code != 0:
            logger.error("gkg_query_failed", stderr=stderr)
            return DependencyResult(
                file_path=file_path,
                repo=repo,
                dependencies=[],
                formatted_output=f"Query failed: {stderr}",
            )

        raw_results = self._parse_json(stdout)
        dependencies = [
            DependencyItem(
                path=r.get("path", "unknown"),
                type=r.get("type", "unknown"),
            )
            for r in raw_results
        ]

        formatted_lines = [f"Dependencies for {file_path}:"]
        for dep in dependencies:
            formatted_lines.append(f"  - {dep.path} ({dep.type})")

        return DependencyResult(
            file_path=file_path,
            repo=repo,
            dependencies=dependencies,
            formatted_output="\n".join(formatted_lines),
        )

    async def find_usages(
        self,
        org_id: str,
        symbol: str,
        repo: str,
    ) -> list[UsageResult]:
        db_path = self._get_db_path(org_id)

        if not db_path.exists():
            return []

        query = f"""
        MATCH (ref)-[:REFERENCES]->(s {{name: '{symbol}'}})
        RETURN ref.file as file, ref.line as line, ref.context as context
        """

        stdout, stderr, code = await self._run_command(
            ["query", "--db", str(db_path), "--format", "json", query],
        )

        if code != 0:
            logger.error("gkg_usage_query_failed", stderr=stderr)
            return []

        raw_results = self._parse_json(stdout)
        return [
            UsageResult(
                file=r.get("file", ""),
                line=r.get("line", 0),
                context=r.get("context", ""),
            )
            for r in raw_results
        ]

    async def get_call_graph(
        self,
        org_id: str,
        repo: str,
        function_name: str,
        direction: str,
        depth: int,
    ) -> CallGraphResult:
        db_path = self._get_db_path(org_id)

        if not db_path.exists():
            return CallGraphResult(
                function_name=function_name,
                callers=[],
                callees=[],
                formatted_graph="No index found",
            )

        callers: list[CallGraphNode] = []
        callees: list[CallGraphNode] = []

        if direction in ("callers", "both"):
            callers = await self._query_callers(db_path, function_name, depth)

        if direction in ("callees", "both"):
            callees = await self._query_callees(db_path, function_name, depth)

        formatted_graph = self._format_call_graph(function_name, callers, callees)

        return CallGraphResult(
            function_name=function_name,
            callers=callers,
            callees=callees,
            formatted_graph=formatted_graph,
        )

    async def _query_callers(
        self,
        db_path: Path,
        function_name: str,
        depth: int,
    ) -> list[CallGraphNode]:
        query = f"""
        MATCH (caller:Function)-[:CALLS*1..{depth}]->(f:Function {{name: '{function_name}'}})
        RETURN caller.name as name, caller.file as file, caller.line as line
        """
        stdout, _, code = await self._run_command(
            ["query", "--db", str(db_path), "--format", "json", query],
        )
        if code != 0:
            return []

        raw_results = self._parse_json(stdout)
        return [
            CallGraphNode(
                name=r.get("name", ""),
                file=r.get("file", ""),
                line=r.get("line"),
            )
            for r in raw_results
        ]

    async def _query_callees(
        self,
        db_path: Path,
        function_name: str,
        depth: int,
    ) -> list[CallGraphNode]:
        query = f"""
        MATCH (f:Function {{name: '{function_name}'}})-[:CALLS*1..{depth}]->(callee:Function)
        RETURN callee.name as name, callee.file as file, callee.line as line
        """
        stdout, _, code = await self._run_command(
            ["query", "--db", str(db_path), "--format", "json", query],
        )
        if code != 0:
            return []

        raw_results = self._parse_json(stdout)
        return [
            CallGraphNode(
                name=r.get("name", ""),
                file=r.get("file", ""),
                line=r.get("line"),
            )
            for r in raw_results
        ]

    def _format_call_graph(
        self,
        function_name: str,
        callers: list[CallGraphNode],
        callees: list[CallGraphNode],
    ) -> str:
        lines = [f"Call Graph for {function_name}:"]
        if callers:
            lines.append("\nCallers:")
            for c in callers:
                lines.append(f"  <- {c.name} ({c.file}:{c.line})")
        if callees:
            lines.append("\nCallees:")
            for c in callees:
                lines.append(f"  -> {c.name} ({c.file}:{c.line})")
        return "\n".join(lines)

    async def get_class_hierarchy(
        self,
        org_id: str,
        class_name: str,
        repo: str,
    ) -> HierarchyResult:
        db_path = self._get_db_path(org_id)

        if not db_path.exists():
            return HierarchyResult(
                class_name=class_name,
                parents=[],
                children=[],
                formatted_hierarchy="No index found",
            )

        parents = await self._query_parents(db_path, class_name)
        children = await self._query_children(db_path, class_name)

        formatted = self._format_hierarchy(class_name, parents, children)

        return HierarchyResult(
            class_name=class_name,
            parents=parents,
            children=children,
            formatted_hierarchy=formatted,
        )

    async def _query_parents(
        self,
        db_path: Path,
        class_name: str,
    ) -> list[HierarchyNode]:
        query = f"""
        MATCH (c:Class {{name: '{class_name}'}})-[:EXTENDS|IMPLEMENTS*1..5]->(parent)
        RETURN parent.name as name, parent.file as file
        """
        stdout, _, code = await self._run_command(
            ["query", "--db", str(db_path), "--format", "json", query],
        )
        if code != 0:
            return []

        raw_results = self._parse_json(stdout)
        return [
            HierarchyNode(name=r.get("name", ""), file=r.get("file", ""))
            for r in raw_results
        ]

    async def _query_children(
        self,
        db_path: Path,
        class_name: str,
    ) -> list[HierarchyNode]:
        query = f"""
        MATCH (child)-[:EXTENDS|IMPLEMENTS*1..5]->(c:Class {{name: '{class_name}'}})
        RETURN child.name as name, child.file as file
        """
        stdout, _, code = await self._run_command(
            ["query", "--db", str(db_path), "--format", "json", query],
        )
        if code != 0:
            return []

        raw_results = self._parse_json(stdout)
        return [
            HierarchyNode(name=r.get("name", ""), file=r.get("file", ""))
            for r in raw_results
        ]

    def _format_hierarchy(
        self,
        class_name: str,
        parents: list[HierarchyNode],
        children: list[HierarchyNode],
    ) -> str:
        lines = [f"Class Hierarchy for {class_name}:"]
        if parents:
            lines.append("\nParents:")
            for p in parents:
                lines.append(f"  ^ {p.name} ({p.file})")
        lines.append(f"\n  [{class_name}]")
        if children:
            lines.append("\nChildren:")
            for c in children:
                lines.append(f"  v {c.name} ({c.file})")
        return "\n".join(lines)

    async def get_related_entities(
        self,
        org_id: str,
        entity: str,
        entity_type: str,
        relationship: str,
    ) -> RelatedEntitiesResult:
        db_path = self._get_db_path(org_id)

        if not db_path.exists():
            return RelatedEntitiesResult(
                entity=entity,
                entity_type=entity_type,
                relationships={},
            )

        rel_types = (
            ["calls", "imports", "extends", "references"]
            if relationship == "all"
            else [relationship]
        )

        relationships: dict[str, list[RelatedEntity]] = {}

        for rel in rel_types:
            query = f"""
            MATCH (e:{entity_type.capitalize()} {{name: '{entity}'}})-[:{rel.upper()}]->(related)
            RETURN related.name as name, related.file as file, related.line as line
            """
            stdout, _, code = await self._run_command(
                ["query", "--db", str(db_path), "--format", "json", query],
            )
            if code == 0:
                raw_results = self._parse_json(stdout)
                relationships[rel] = [
                    RelatedEntity(
                        name=r.get("name", ""),
                        file=r.get("file", ""),
                        line=r.get("line"),
                    )
                    for r in raw_results
                ]

        return RelatedEntitiesResult(
            entity=entity,
            entity_type=entity_type,
            relationships=relationships,
        )

    async def index_repo(self, org_id: str, repo_path: str) -> bool:
        logger.info("gkg_indexing_repo", org_id=org_id, repo_path=repo_path)

        output_dir = self._data_dir / org_id
        output_dir.mkdir(parents=True, exist_ok=True)

        _, stderr, code = await self._run_command(
            ["index", "--output", str(output_dir)],
            cwd=repo_path,
        )

        if code != 0:
            logger.error("gkg_index_failed", stderr=stderr)
            return False

        logger.info("gkg_index_completed", org_id=org_id)
        return True

    async def get_indexed_count(self, org_id: str | None = None) -> int:
        if org_id:
            org_path = self._data_dir / org_id
            if org_path.exists():
                return len(list(org_path.glob("*.db")))
            return 0

        count = 0
        if self._data_dir.exists():
            for org_dir in self._data_dir.iterdir():
                if org_dir.is_dir():
                    count += len(list(org_dir.glob("*.db")))
        return count

    def _parse_json(self, stdout: str) -> list[dict]:
        if not stdout.strip():
            return []
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return []
