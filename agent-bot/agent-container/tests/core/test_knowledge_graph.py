import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from core.knowledge_graph.indexer import KnowledgeGraphIndexer
from core.knowledge_graph.models import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    IndexResult,
)
from core.knowledge_graph.query import KnowledgeGraphQuery


@pytest.fixture
def indexer() -> KnowledgeGraphIndexer:
    return KnowledgeGraphIndexer()


@pytest.fixture
def sample_python_code() -> str:
    return '''
class TaskProcessor:
    def __init__(self, queue):
        self.queue = queue

    def process(self, task):
        result = self._validate(task)
        return self._execute(result)

    def _validate(self, task):
        return task

    def _execute(self, task):
        return task

def helper_function():
    processor = TaskProcessor(None)
    return processor.process({})
'''


class TestKnowledgeGraphIndexerParsePython:
    def test_extracts_classes(
        self, indexer: KnowledgeGraphIndexer, sample_python_code: str
    ):
        entities, relations = indexer._parse_python_content(
            sample_python_code, "test.py"
        )

        classes = [e for e in entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "TaskProcessor"

    def test_extracts_methods(
        self, indexer: KnowledgeGraphIndexer, sample_python_code: str
    ):
        entities, relations = indexer._parse_python_content(
            sample_python_code, "test.py"
        )

        methods = [e for e in entities if e.type == EntityType.METHOD]
        method_names = {m.name for m in methods}
        assert "__init__" in method_names
        assert "process" in method_names
        assert "_validate" in method_names

    def test_extracts_functions(
        self, indexer: KnowledgeGraphIndexer, sample_python_code: str
    ):
        entities, relations = indexer._parse_python_content(
            sample_python_code, "test.py"
        )

        functions = [e for e in entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].name == "helper_function"

    def test_extracts_call_relations(
        self, indexer: KnowledgeGraphIndexer, sample_python_code: str
    ):
        entities, relations = indexer._parse_python_content(
            sample_python_code, "test.py"
        )

        calls = [r for r in relations if r.type == RelationType.CALLS]
        assert len(calls) > 0


class TestKnowledgeGraphIndexerIndexRepo:
    @pytest.mark.asyncio
    async def test_indexes_repository(
        self, indexer: KnowledgeGraphIndexer, tmp_path: Path
    ):
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "utils.py").write_text("def helper(): pass")
        (tmp_path / ".git").mkdir()

        with patch.object(indexer, "_get_commit_hash") as mock_hash:
            mock_hash.return_value = "abc123"

            result = await indexer.index_repository(tmp_path)

            assert result.entities_count > 0
            assert result.commit_hash == "abc123"

    @pytest.mark.asyncio
    async def test_skips_non_python_files(
        self, indexer: KnowledgeGraphIndexer, tmp_path: Path
    ):
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "readme.md").write_text("# README")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / ".git").mkdir()

        with patch.object(indexer, "_get_commit_hash") as mock_hash:
            mock_hash.return_value = "abc123"

            result = await indexer.index_repository(tmp_path)

            assert result.entities_count == 2


class TestKnowledgeGraphQuery:
    def test_find_function_callers(self):
        func = Entity(
            id="func-1",
            type=EntityType.FUNCTION,
            name="target_func",
            file_path="main.py",
            line_number=10,
        )
        caller = Entity(
            id="func-2",
            type=EntityType.FUNCTION,
            name="caller_func",
            file_path="main.py",
            line_number=20,
        )
        relation = Relation(
            source_id="func-2",
            target_id="func-1",
            type=RelationType.CALLS,
        )

        query_client = KnowledgeGraphQuery(
            entities=[func, caller],
            relations=[relation]
        )

        callers = query_client.find_callers("target_func")

        assert len(callers) == 1
        assert callers[0].name == "caller_func"

    def test_find_affected_by_change(self):
        file1 = Entity(
            id="file-1",
            type=EntityType.FILE,
            name="core.py",
            file_path="src/core.py",
        )
        file2 = Entity(
            id="file-2",
            type=EntityType.FILE,
            name="main.py",
            file_path="src/main.py",
        )
        import_rel = Relation(
            source_id="file-2",
            target_id="file-1",
            type=RelationType.IMPORTS,
        )

        query_client = KnowledgeGraphQuery(
            entities=[file1, file2],
            relations=[import_rel]
        )

        affected = query_client.find_affected_by_change("src/core.py")

        assert "src/main.py" in affected
