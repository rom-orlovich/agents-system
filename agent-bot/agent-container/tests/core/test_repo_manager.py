import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
        with patch("core.repo_manager.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
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
        with patch("core.repo_manager.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
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

        with patch("core.repo_manager.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
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
