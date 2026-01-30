import subprocess
import structlog
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone

logger = structlog.get_logger()


@dataclass
class RepoConfig:
    base_path: Path = Path("/data/repos")
    max_repo_size_mb: int = 500
    shallow_clone_depth: int = 1
    cache_ttl_hours: int = 24


class RepoManager:
    def __init__(self, config: RepoConfig | None = None):
        self.config = config or RepoConfig()
        self.config.base_path.mkdir(parents=True, exist_ok=True)

    async def ensure_repo(
        self,
        organization_id: str,
        repo_full_name: str,
        access_token: str,
        ref: str = "main",
    ) -> Path:
        logger.info(
            "ensuring_repo",
            org_id=organization_id,
            repo=repo_full_name,
            ref=ref,
        )

        repo_path = self._get_repo_path(organization_id, repo_full_name)

        if repo_path.exists():
            logger.info("repo_exists_updating", path=str(repo_path))
            await self._update_repo(repo_path, ref, access_token)
        else:
            logger.info("repo_not_found_cloning", path=str(repo_path))
            await self._clone_repo(
                organization_id, repo_full_name, access_token, ref
            )

        return repo_path

    async def _clone_repo(
        self,
        organization_id: str,
        repo_full_name: str,
        access_token: str,
        ref: str,
    ) -> Path:
        repo_path = self._get_repo_path(organization_id, repo_full_name)
        repo_path.parent.mkdir(parents=True, exist_ok=True)

        clone_url = f"https://x-access-token:{access_token}@github.com/{repo_full_name}.git"

        cmd = [
            "git",
            "clone",
            "--depth",
            str(self.config.shallow_clone_depth),
            "--branch",
            ref,
            "--single-branch",
            clone_url,
            str(repo_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )

            logger.info("repo_cloned", path=str(repo_path))

            await self._sanitize_remote(repo_path, repo_full_name)

            return repo_path

        except subprocess.CalledProcessError as e:
            logger.error(
                "clone_failed",
                error=e.stderr,
                repo=repo_full_name,
            )
            raise
        except subprocess.TimeoutExpired:
            logger.error("clone_timeout", repo=repo_full_name)
            raise

    async def _update_repo(
        self, repo_path: Path, ref: str, access_token: str
    ) -> None:
        logger.info("updating_repo", path=str(repo_path), ref=ref)

        try:
            subprocess.run(
                ["git", "-C", str(repo_path), "fetch", "origin", ref],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )

            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "checkout",
                    f"origin/{ref}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )

            logger.info("repo_updated", path=str(repo_path))

        except subprocess.CalledProcessError as e:
            logger.error("update_failed", error=e.stderr)
            raise

    async def checkout_pr(self, repo_path: Path, pr_number: int) -> None:
        logger.info("checking_out_pr", path=str(repo_path), pr=pr_number)

        try:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "fetch",
                    "origin",
                    f"pull/{pr_number}/head:pr-{pr_number}",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )

            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "checkout",
                    f"pr-{pr_number}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )

            logger.info("pr_checked_out", pr=pr_number)

        except subprocess.CalledProcessError as e:
            logger.error("pr_checkout_failed", error=e.stderr, pr=pr_number)
            raise

    async def _sanitize_remote(
        self, repo_path: Path, repo_full_name: str
    ) -> None:
        safe_url = f"https://github.com/{repo_full_name}.git"

        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "remote",
                "set-url",
                "origin",
                safe_url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        logger.info("remote_sanitized", repo=repo_full_name)

    def _get_repo_path(
        self, organization_id: str, repo_full_name: str
    ) -> Path:
        safe_name = repo_full_name.replace("/", "_")
        return self.config.base_path / organization_id / safe_name

    async def cleanup_old_repos(self) -> int:
        logger.info("cleaning_old_repos")

        removed = 0
        cutoff_timestamp = datetime.now(timezone.utc).timestamp() - (
            self.config.cache_ttl_hours * 3600
        )

        for org_path in self.config.base_path.iterdir():
            if not org_path.is_dir():
                continue

            for repo_path in org_path.iterdir():
                if not repo_path.is_dir():
                    continue

                if repo_path.stat().st_atime < cutoff_timestamp:
                    logger.info("removing_old_repo", path=str(repo_path))
                    import shutil

                    shutil.rmtree(repo_path)
                    removed += 1

        logger.info("cleanup_complete", removed=removed)
        return removed
