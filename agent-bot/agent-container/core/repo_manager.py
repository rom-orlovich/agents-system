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
    model_config = ConfigDict(strict=True, extra="forbid", arbitrary_types_allowed=True)

    path: Path
    organization_id: str
    repo_full_name: str
    ref: str
    last_updated: datetime


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
