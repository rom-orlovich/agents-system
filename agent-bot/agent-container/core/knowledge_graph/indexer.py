import ast
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import structlog

from .models import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    IndexResult,
)

logger = structlog.get_logger()


class KnowledgeGraphIndexer:
    SUPPORTED_EXTENSIONS = {".py", ".ts", ".js", ".tsx", ".jsx"}

    def __init__(self) -> None:
        self._entities: list[Entity] = []
        self._relations: list[Relation] = []

    async def index_repository(self, repo_path: Path) -> IndexResult:
        start_time = time.time()
        self._entities = []
        self._relations = []

        commit_hash = await self._get_commit_hash(repo_path)

        for file_path in self._iter_source_files(repo_path):
            try:
                await self._index_file(file_path, repo_path)
            except Exception as e:
                logger.warning(
                    "index_file_failed",
                    file=str(file_path),
                    error=str(e),
                )

        duration = time.time() - start_time

        logger.info(
            "repository_indexed",
            repo=str(repo_path),
            entities=len(self._entities),
            relations=len(self._relations),
            duration=duration,
        )

        return IndexResult(
            repo_path=str(repo_path),
            commit_hash=commit_hash,
            entities_count=len(self._entities),
            relations_count=len(self._relations),
            indexed_at=datetime.now(timezone.utc),
            duration_seconds=duration,
        )

    def get_entities(self) -> list[Entity]:
        return self._entities.copy()

    def get_relations(self) -> list[Relation]:
        return self._relations.copy()

    async def _index_file(self, file_path: Path, repo_path: Path) -> None:
        relative_path = str(file_path.relative_to(repo_path))
        content = file_path.read_text(encoding="utf-8", errors="ignore")

        file_entity = Entity(
            id=f"file-{uuid4().hex[:8]}",
            type=EntityType.FILE,
            name=file_path.name,
            file_path=relative_path,
        )
        self._entities.append(file_entity)

        if file_path.suffix == ".py":
            entities, relations = self._parse_python_content(
                content, relative_path
            )
            self._entities.extend(entities)
            self._relations.extend(relations)

    def _parse_python_content(
        self, content: str, file_path: str
    ) -> tuple[list[Entity], list[Relation]]:
        entities: list[Entity] = []
        relations: list[Relation] = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return entities, relations

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_entity = Entity(
                    id=f"class-{uuid4().hex[:8]}",
                    type=EntityType.CLASS,
                    name=node.name,
                    file_path=file_path,
                    line_number=node.lineno,
                    end_line_number=node.end_lineno,
                )
                entities.append(class_entity)

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_entity = Entity(
                            id=f"method-{uuid4().hex[:8]}",
                            type=EntityType.METHOD,
                            name=item.name,
                            file_path=file_path,
                            line_number=item.lineno,
                            end_line_number=item.end_lineno,
                            metadata={"class": node.name},
                        )
                        entities.append(method_entity)

            elif isinstance(node, ast.FunctionDef):
                if not self._is_method(node, tree):
                    func_entity = Entity(
                        id=f"func-{uuid4().hex[:8]}",
                        type=EntityType.FUNCTION,
                        name=node.name,
                        file_path=file_path,
                        line_number=node.lineno,
                        end_line_number=node.end_lineno,
                    )
                    entities.append(func_entity)

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    relations.append(
                        Relation(
                            source_id=f"file:{file_path}",
                            target_id=f"func:{node.func.id}",
                            type=RelationType.CALLS,
                            metadata={"line": str(node.lineno)},
                        )
                    )

        return entities, relations

    def _is_method(self, node: ast.FunctionDef, tree: ast.Module) -> bool:
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                if node in parent.body:
                    return True
        return False

    def _iter_source_files(self, repo_path: Path):
        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
                continue
            if ".git" in file_path.parts:
                continue
            if "node_modules" in file_path.parts:
                continue
            if "__pycache__" in file_path.parts:
                continue
            yield file_path

    async def _get_commit_hash(self, repo_path: Path) -> str:
        process = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "HEAD",
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        return stdout.decode().strip()[:12]
