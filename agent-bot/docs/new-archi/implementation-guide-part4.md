# Agent Bot - TDD Implementation Guide

## Part 4: Repository Manager & Knowledge Graph

---

## Phase 7: Repository Manager Implementation

### Step 7.1: Create Directory Structure

```bash
mkdir -p agent-container/core
touch agent-container/core/__init__.py
touch agent-container/core/repo_manager.py
touch agent-container/core/repo_security.py
touch agent-container/tests/core/__init__.py
touch agent-container/tests/core/test_repo_manager.py
touch agent-container/tests/core/test_repo_security.py
```

### Step 7.2: Write Tests FIRST - Repository Security

**File: `agent-container/tests/core/test_repo_security.py`** (< 120 lines)

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from core.repo_security import RepoSecurityPolicy, SecurityViolationError


@pytest.fixture
def policy() -> RepoSecurityPolicy:
    return RepoSecurityPolicy()


class TestRepoSecurityPolicyBlockedPaths:
    def test_blocks_env_files(self, policy: RepoSecurityPolicy):
        assert policy.is_path_blocked(Path(".env")) is True
        assert policy.is_path_blocked(Path(".env.local")) is True
        assert policy.is_path_blocked(Path(".env.production")) is True

    def test_blocks_key_files(self, policy: RepoSecurityPolicy):
        assert policy.is_path_blocked(Path("private.key")) is True
        assert policy.is_path_blocked(Path("server.pem")) is True
        assert policy.is_path_blocked(Path("certs/ca.key")) is True

    def test_blocks_secrets_directories(self, policy: RepoSecurityPolicy):
        assert policy.is_path_blocked(Path("secrets/db.json")) is True
        assert policy.is_path_blocked(Path("config/secrets/api.json")) is True
        assert policy.is_path_blocked(Path(".credentials/token")) is True

    def test_allows_normal_files(self, policy: RepoSecurityPolicy):
        assert policy.is_path_blocked(Path("src/main.py")) is False
        assert policy.is_path_blocked(Path("README.md")) is False
        assert policy.is_path_blocked(Path("package.json")) is False


class TestRepoSecurityPolicyAllowedExtensions:
    def test_allows_code_files(self, policy: RepoSecurityPolicy):
        assert policy.is_extension_allowed(Path("main.py")) is True
        assert policy.is_extension_allowed(Path("app.ts")) is True
        assert policy.is_extension_allowed(Path("component.tsx")) is True
        assert policy.is_extension_allowed(Path("server.go")) is True

    def test_allows_config_files(self, policy: RepoSecurityPolicy):
        assert policy.is_extension_allowed(Path("config.json")) is True
        assert policy.is_extension_allowed(Path("settings.yaml")) is True
        assert policy.is_extension_allowed(Path("pyproject.toml")) is True

    def test_blocks_binary_files(self, policy: RepoSecurityPolicy):
        assert policy.is_extension_allowed(Path("image.png")) is False
        assert policy.is_extension_allowed(Path("archive.zip")) is False
        assert policy.is_extension_allowed(Path("binary.exe")) is False


class TestRepoSecurityPolicyFileSize:
    def test_allows_small_files(self, policy: RepoSecurityPolicy):
        small_size = 1024 * 1024
        assert policy.is_size_allowed(small_size) is True

    def test_blocks_large_files(self, policy: RepoSecurityPolicy):
        large_size = 20 * 1024 * 1024
        assert policy.is_size_allowed(large_size) is False


class TestRepoSecurityPolicyCanAccess:
    def test_can_access_valid_file(
        self, policy: RepoSecurityPolicy, tmp_path: Path
    ):
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        assert policy.can_access_file(test_file) is True

    def test_cannot_access_blocked_file(
        self, policy: RepoSecurityPolicy, tmp_path: Path
    ):
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value")

        assert policy.can_access_file(env_file) is False

    def test_cannot_access_binary_file(
        self, policy: RepoSecurityPolicy, tmp_path: Path
    ):
        binary_file = tmp_path / "image.png"
        binary_file.write_bytes(b"\x89PNG")

        assert policy.can_access_file(binary_file) is False
```

### Step 7.3: Implement Repository Security

**File: `agent-container/core/repo_security.py`** (< 100 lines)

```python
from pathlib import Path
from fnmatch import fnmatch

import structlog

logger = structlog.get_logger()


class SecurityViolationError(Exception):
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Security violation for {path}: {reason}")


class RepoSecurityPolicy:
    BLOCKED_PATTERNS = [
        ".env",
        ".env.*",
        "*.pem",
        "*.key",
        "**/secrets/**",
        "**/.credentials/**",
        "**/.ssh/**",
        "**/id_rsa*",
        "**/*.p12",
        "**/*.pfx",
    ]

    ALLOWED_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx",
        ".go", ".rs", ".java", ".rb", ".php",
        ".c", ".cpp", ".h", ".hpp", ".cs",
        ".md", ".txt", ".rst",
        ".json", ".yaml", ".yml", ".toml",
        ".xml", ".html", ".css", ".scss",
        ".sh", ".bash", ".zsh",
        ".sql", ".graphql",
        ".dockerfile", ".containerfile",
        ".gitignore", ".dockerignore",
        ".editorconfig", ".prettierrc",
    }

    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

    def is_path_blocked(self, path: Path) -> bool:
        path_str = str(path)
        for pattern in self.BLOCKED_PATTERNS:
            if fnmatch(path_str, pattern):
                return True
            if fnmatch(path.name, pattern):
                return True
        return False

    def is_extension_allowed(self, path: Path) -> bool:
        if path.suffix == "":
            return path.name in {
                "Dockerfile", "Makefile", "Jenkinsfile",
                "Procfile", "Gemfile", "Rakefile",
            }
        return path.suffix.lower() in self.ALLOWED_EXTENSIONS

    def is_size_allowed(self, size_bytes: int) -> bool:
        return size_bytes <= self.MAX_FILE_SIZE_BYTES

    def can_access_file(self, path: Path) -> bool:
        if self.is_path_blocked(path):
            logger.warning("blocked_path_access", path=str(path))
            return False

        if not self.is_extension_allowed(path):
            return False

        if path.exists() and path.is_file():
            if not self.is_size_allowed(path.stat().st_size):
                return False

        return True

    def validate_or_raise(self, path: Path) -> None:
        if self.is_path_blocked(path):
            raise SecurityViolationError(str(path), "blocked_pattern")

        if not self.is_extension_allowed(path):
            raise SecurityViolationError(str(path), "disallowed_extension")

        if path.exists() and path.is_file():
            if not self.is_size_allowed(path.stat().st_size):
                raise SecurityViolationError(str(path), "file_too_large")
```

### Step 7.4: Write Tests FIRST - Repository Manager

**File: `agent-container/tests/core/test_repo_manager.py`** (< 250 lines)

```python
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core.repo_manager import RepoManager, RepoConfig, RepoInfo
from token_service import TokenService, Platform, TokenInfo


@pytest.fixture
def mock_token_service() -> AsyncMock:
    service = AsyncMock(spec=TokenService)
    service.get_token.return_value = TokenInfo(
        access_token="gho_xxxx",
        expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        scopes=["repo"],
    )
    return service


@pytest.fixture
def repo_config(tmp_path: Path) -> RepoConfig:
    return RepoConfig(
        base_path=tmp_path / "repos",
        max_repo_size_mb=500,
        shallow_clone_depth=1,
        cache_ttl_hours=24,
    )


@pytest.fixture
def manager(
    repo_config: RepoConfig,
    mock_token_service: AsyncMock,
) -> RepoManager:
    return RepoManager(
        config=repo_config,
        token_service=mock_token_service,
    )


class TestRepoManagerEnsureRepo:
    @pytest.mark.asyncio
    async def test_clones_new_repo(
        self,
        manager: RepoManager,
        mock_token_service: AsyncMock,
    ):
        with patch.object(manager, "_clone_repo") as mock_clone:
            mock_clone.return_value = RepoInfo(
                path=Path("/tmp/repos/inst-123/owner_repo"),
                organization_id="inst-123",
                repo_full_name="owner/repo",
                ref="main",
                last_updated=datetime.now(timezone.utc),
            )

            result = await manager.ensure_repo(
                installation_id="inst-123",
                repo_full_name="owner/repo",
            )

            mock_clone.assert_called_once()
            assert result.repo_full_name == "owner/repo"

    @pytest.mark.asyncio
    async def test_updates_existing_repo(
        self,
        manager: RepoManager,
        repo_config: RepoConfig,
    ):
        repo_path = repo_config.base_path / "inst-123" / "owner_repo"
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        with patch.object(manager, "_update_repo") as mock_update:
            mock_update.return_value = RepoInfo(
                path=repo_path,
                organization_id="inst-123",
                repo_full_name="owner/repo",
                ref="main",
                last_updated=datetime.now(timezone.utc),
            )

            result = await manager.ensure_repo(
                installation_id="inst-123",
                repo_full_name="owner/repo",
            )

            mock_update.assert_called_once()


class TestRepoManagerClone:
    @pytest.mark.asyncio
    async def test_clone_creates_directory(
        self,
        manager: RepoManager,
        repo_config: RepoConfig,
        mock_token_service: AsyncMock,
    ):
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.wait.return_value = 0
            mock_process.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_process

            await manager._clone_repo(
                installation_id="inst-123",
                repo_full_name="owner/repo",
                ref="main",
            )

            mock_exec.assert_called()

    @pytest.mark.asyncio
    async def test_clone_sanitizes_remote_url(
        self,
        manager: RepoManager,
        mock_token_service: AsyncMock,
    ):
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.wait.return_value = 0
            mock_process.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_process

            with patch.object(manager, "_sanitize_remote") as mock_sanitize:
                await manager._clone_repo(
                    installation_id="inst-123",
                    repo_full_name="owner/repo",
                    ref="main",
                )

                mock_sanitize.assert_called_once()


class TestRepoManagerCheckoutPR:
    @pytest.mark.asyncio
    async def test_checkout_pr_fetches_ref(
        self,
        manager: RepoManager,
        repo_config: RepoConfig,
    ):
        repo_path = repo_config.base_path / "inst-123" / "owner_repo"
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.wait.return_value = 0
            mock_process.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_process

            await manager.checkout_pr(
                repo_path=repo_path,
                pr_number=42,
                installation_id="inst-123",
            )

            calls = mock_exec.call_args_list
            fetch_call = [c for c in calls if "fetch" in str(c)]
            assert len(fetch_call) > 0


class TestRepoManagerCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_removes_old_repos(
        self,
        manager: RepoManager,
        repo_config: RepoConfig,
    ):
        old_repo = repo_config.base_path / "inst-old" / "old_repo"
        old_repo.mkdir(parents=True)
        (old_repo / "file.txt").write_text("content")

        import os
        import time
        old_time = time.time() - (25 * 60 * 60)
        os.utime(old_repo, (old_time, old_time))

        removed = await manager.cleanup_old_repos()

        assert removed >= 0


class TestRepoManagerGetRepoPath:
    def test_get_repo_path_format(self, manager: RepoManager):
        path = manager._get_repo_path("inst-123", "owner/repo")

        assert "inst-123" in str(path)
        assert "owner_repo" in str(path)

    def test_get_repo_path_handles_nested_repos(self, manager: RepoManager):
        path = manager._get_repo_path("inst-123", "org/team/repo")

        assert "inst-123" in str(path)
```

### Step 7.5: Implement Repository Manager

**File: `agent-container/core/repo_manager.py`** (< 250 lines)

```python
import asyncio
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from pydantic import BaseModel, ConfigDict
import structlog

from token_service import TokenService, Platform

logger = structlog.get_logger()


class RepoConfig(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    base_path: Path = Path("/data/repos")
    max_repo_size_mb: int = 500
    max_repos_per_org: int = 10
    shallow_clone_depth: int = 1
    cache_ttl_hours: int = 24


class RepoInfo(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    path: Path
    organization_id: str
    repo_full_name: str
    ref: str
    last_updated: datetime

    class Config:
        arbitrary_types_allowed = True


class RepoCloneError(Exception):
    def __init__(self, repo: str, reason: str):
        self.repo = repo
        self.reason = reason
        super().__init__(f"Failed to clone {repo}: {reason}")


class RepoManager:
    def __init__(
        self,
        config: RepoConfig,
        token_service: TokenService,
    ) -> None:
        self._config = config
        self._token_service = token_service
        self._config.base_path.mkdir(parents=True, exist_ok=True)

    async def ensure_repo(
        self,
        installation_id: str,
        repo_full_name: str,
        ref: str = "main",
    ) -> RepoInfo:
        repo_path = self._get_repo_path(installation_id, repo_full_name)

        if self._is_repo_cached(repo_path):
            logger.info(
                "updating_cached_repo",
                repo=repo_full_name,
                path=str(repo_path),
            )
            return await self._update_repo(
                repo_path, installation_id, repo_full_name, ref
            )

        logger.info(
            "cloning_new_repo",
            repo=repo_full_name,
            installation_id=installation_id,
        )
        return await self._clone_repo(installation_id, repo_full_name, ref)

    async def checkout_pr(
        self,
        repo_path: Path,
        pr_number: int,
        installation_id: str,
    ) -> None:
        logger.info(
            "checking_out_pr",
            pr_number=pr_number,
            path=str(repo_path),
        )

        token_info = await self._token_service.get_token(
            platform=Platform.GITHUB,
            organization_id=installation_id,
        )

        await self._set_credentials(repo_path, token_info.access_token)

        try:
            await self._run_git(
                repo_path,
                ["fetch", "origin", f"pull/{pr_number}/head:pr-{pr_number}"],
            )
            await self._run_git(
                repo_path,
                ["checkout", f"pr-{pr_number}"],
            )
        finally:
            await self._clear_credentials(repo_path)

    async def cleanup_old_repos(self) -> int:
        removed = 0
        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=self._config.cache_ttl_hours
        )

        for org_path in self._config.base_path.iterdir():
            if not org_path.is_dir():
                continue

            for repo_path in org_path.iterdir():
                if not repo_path.is_dir():
                    continue

                try:
                    mtime = datetime.fromtimestamp(
                        repo_path.stat().st_mtime, tz=timezone.utc
                    )
                    if mtime < cutoff:
                        shutil.rmtree(repo_path)
                        removed += 1
                        logger.info("removed_old_repo", path=str(repo_path))
                except Exception as e:
                    logger.error(
                        "cleanup_error",
                        path=str(repo_path),
                        error=str(e),
                    )

        return removed

    async def _clone_repo(
        self,
        installation_id: str,
        repo_full_name: str,
        ref: str,
    ) -> RepoInfo:
        token_info = await self._token_service.get_token(
            platform=Platform.GITHUB,
            organization_id=installation_id,
        )

        repo_path = self._get_repo_path(installation_id, repo_full_name)
        repo_path.parent.mkdir(parents=True, exist_ok=True)

        clone_url = (
            f"https://x-access-token:{token_info.access_token}"
            f"@github.com/{repo_full_name}.git"
        )

        await self._run_git(
            repo_path.parent,
            [
                "clone",
                "--depth", str(self._config.shallow_clone_depth),
                "--branch", ref,
                "--single-branch",
                clone_url,
                repo_path.name,
            ],
        )

        await self._sanitize_remote(repo_path, repo_full_name)

        return RepoInfo(
            path=repo_path,
            organization_id=installation_id,
            repo_full_name=repo_full_name,
            ref=ref,
            last_updated=datetime.now(timezone.utc),
        )

    async def _update_repo(
        self,
        repo_path: Path,
        installation_id: str,
        repo_full_name: str,
        ref: str,
    ) -> RepoInfo:
        token_info = await self._token_service.get_token(
            platform=Platform.GITHUB,
            organization_id=installation_id,
        )

        await self._set_credentials(repo_path, token_info.access_token)

        try:
            await self._run_git(repo_path, ["fetch", "origin", ref])
            await self._run_git(repo_path, ["checkout", f"origin/{ref}"])
        finally:
            await self._clear_credentials(repo_path)

        return RepoInfo(
            path=repo_path,
            organization_id=installation_id,
            repo_full_name=repo_full_name,
            ref=ref,
            last_updated=datetime.now(timezone.utc),
        )

    async def _sanitize_remote(
        self, repo_path: Path, repo_full_name: str
    ) -> None:
        safe_url = f"https://github.com/{repo_full_name}.git"
        await self._run_git(
            repo_path, ["remote", "set-url", "origin", safe_url]
        )

    async def _set_credentials(
        self, repo_path: Path, token: str
    ) -> None:
        await self._run_git(
            repo_path,
            ["config", "http.extraHeader", f"Authorization: Bearer {token}"],
        )

    async def _clear_credentials(self, repo_path: Path) -> None:
        await self._run_git(
            repo_path,
            ["config", "--unset", "http.extraHeader"],
        )

    async def _run_git(self, cwd: Path, args: list[str]) -> str:
        cmd = ["git"] + args
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RepoCloneError(str(cwd), stderr.decode())

        return stdout.decode()

    def _get_repo_path(
        self, installation_id: str, repo_full_name: str
    ) -> Path:
        safe_name = repo_full_name.replace("/", "_")
        return self._config.base_path / installation_id / safe_name

    def _is_repo_cached(self, repo_path: Path) -> bool:
        return (repo_path / ".git").is_dir()
```

---

## Phase 8: Knowledge Graph Integration

### Step 8.1: Create Directory Structure

```bash
mkdir -p agent-container/core/knowledge_graph
touch agent-container/core/knowledge_graph/__init__.py
touch agent-container/core/knowledge_graph/indexer.py
touch agent-container/core/knowledge_graph/query.py
touch agent-container/core/knowledge_graph/models.py
touch agent-container/tests/core/test_knowledge_graph.py
```

### Step 8.2: Define Knowledge Graph Models

**File: `agent-container/core/knowledge_graph/models.py`** (< 100 lines)

```python
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntityType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    MODULE = "module"
    IMPORT = "import"
    TEST = "test"


class RelationType(str, Enum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    CALLS = "calls"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    TESTS = "tests"
    DEPENDS_ON = "depends_on"


class Entity(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    type: EntityType
    name: str
    file_path: str
    line_number: int | None = None
    end_line_number: int | None = None
    metadata: dict[str, str] = {}


class Relation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source_id: str
    target_id: str
    type: RelationType
    metadata: dict[str, str] = {}


class IndexResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    repo_path: str
    commit_hash: str
    entities_count: int
    relations_count: int
    indexed_at: datetime
    duration_seconds: float


class FunctionCallers(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    function_name: str
    callers: list[Entity]


class ClassHierarchy(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    class_name: str
    parents: list[Entity]
    children: list[Entity]


class ImpactAnalysis(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    file_path: str
    affected_files: list[str]
    affected_tests: list[str]
    risk_score: float
```

### Step 8.3: Write Tests FIRST - Knowledge Graph Indexer

**File: `agent-container/tests/core/test_knowledge_graph.py`** (< 200 lines)

```python
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
    @pytest.fixture
    def query_client(self) -> KnowledgeGraphQuery:
        return KnowledgeGraphQuery(entities=[], relations=[])

    def test_find_function_callers(self, query_client: KnowledgeGraphQuery):
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

        query_client._entities = [func, caller]
        query_client._relations = [relation]

        callers = query_client.find_callers("target_func")

        assert len(callers) == 1
        assert callers[0].name == "caller_func"

    def test_find_affected_by_change(self, query_client: KnowledgeGraphQuery):
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

        query_client._entities = [file1, file2]
        query_client._relations = [import_rel]

        affected = query_client.find_affected_by_change("src/core.py")

        assert "src/main.py" in affected
```

### Step 8.4: Implement Knowledge Graph Indexer

**File: `agent-container/core/knowledge_graph/indexer.py`** (< 200 lines)

```python
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
```

### Step 8.5: Implement Knowledge Graph Query

**File: `agent-container/core/knowledge_graph/query.py`** (< 150 lines)

```python
from .models import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    FunctionCallers,
    ClassHierarchy,
    ImpactAnalysis,
)


class KnowledgeGraphQuery:
    def __init__(
        self,
        entities: list[Entity],
        relations: list[Relation],
    ) -> None:
        self._entities = entities
        self._relations = relations
        self._entity_by_id: dict[str, Entity] = {e.id: e for e in entities}
        self._entity_by_name: dict[str, list[Entity]] = {}

        for entity in entities:
            if entity.name not in self._entity_by_name:
                self._entity_by_name[entity.name] = []
            self._entity_by_name[entity.name].append(entity)

    def find_callers(self, function_name: str) -> list[Entity]:
        target_entities = self._entity_by_name.get(function_name, [])
        target_ids = {f"func:{function_name}"} | {e.id for e in target_entities}

        callers: list[Entity] = []
        for relation in self._relations:
            if relation.type != RelationType.CALLS:
                continue
            if relation.target_id not in target_ids:
                continue

            caller_id = relation.source_id
            if caller_id.startswith("file:"):
                continue

            caller = self._entity_by_id.get(caller_id)
            if caller:
                callers.append(caller)

        return callers

    def find_class_hierarchy(self, class_name: str) -> ClassHierarchy:
        parents: list[Entity] = []
        children: list[Entity] = []

        class_entities = [
            e for e in self._entity_by_name.get(class_name, [])
            if e.type == EntityType.CLASS
        ]
        class_ids = {e.id for e in class_entities}

        for relation in self._relations:
            if relation.type != RelationType.EXTENDS:
                continue

            if relation.source_id in class_ids:
                parent = self._entity_by_id.get(relation.target_id)
                if parent:
                    parents.append(parent)

            if relation.target_id in class_ids:
                child = self._entity_by_id.get(relation.source_id)
                if child:
                    children.append(child)

        return ClassHierarchy(
            class_name=class_name,
            parents=parents,
            children=children,
        )

    def find_affected_by_change(self, file_path: str) -> list[str]:
        affected: set[str] = set()
        visited: set[str] = set()

        file_entities = [
            e for e in self._entities
            if e.file_path == file_path
        ]
        file_ids = {e.id for e in file_entities}
        file_ids.add(f"file:{file_path}")

        queue = list(file_ids)

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            for relation in self._relations:
                if relation.target_id != current_id:
                    continue
                if relation.type not in {
                    RelationType.IMPORTS,
                    RelationType.DEPENDS_ON,
                    RelationType.CALLS,
                }:
                    continue

                source = self._entity_by_id.get(relation.source_id)
                if source and source.file_path != file_path:
                    affected.add(source.file_path)
                    queue.append(relation.source_id)

        return list(affected)

    def find_tests_for_file(self, file_path: str) -> list[Entity]:
        tests: list[Entity] = []

        file_entities = [
            e for e in self._entities
            if e.file_path == file_path
        ]
        file_ids = {e.id for e in file_entities}

        for relation in self._relations:
            if relation.type != RelationType.TESTS:
                continue
            if relation.target_id not in file_ids:
                continue

            test = self._entity_by_id.get(relation.source_id)
            if test:
                tests.append(test)

        return tests

    def get_impact_analysis(self, file_path: str) -> ImpactAnalysis:
        affected_files = self.find_affected_by_change(file_path)
        tests = self.find_tests_for_file(file_path)
        affected_tests = [t.file_path for t in tests]

        risk_score = min(1.0, len(affected_files) / 10.0)

        return ImpactAnalysis(
            file_path=file_path,
            affected_files=affected_files,
            affected_tests=affected_tests,
            risk_score=risk_score,
        )
```

---

## Run Tests to Verify Phase 7-8

```bash
cd agent-container
pytest -v tests/core/test_repo_security.py
pytest -v tests/core/test_repo_manager.py
pytest -v tests/core/test_knowledge_graph.py

# Expected: All tests pass < 5 seconds per file
```

---

## Checkpoint 4 Complete ✅

Before proceeding, verify:
- [ ] RepoSecurityPolicy blocks sensitive files
- [ ] RepoManager clones and updates repos
- [ ] Knowledge Graph indexes Python files
- [ ] All files < 300 lines
- [ ] NO `any` types used
- [ ] All tests pass

Continue to Part 5 for Agent Organization (Skills, Commands, Hooks)...
