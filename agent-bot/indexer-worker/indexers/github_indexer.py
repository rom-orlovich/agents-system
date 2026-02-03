import hashlib
from pathlib import Path
from fnmatch import fnmatch
import structlog
import httpx
from git import Repo

from config import settings
from models import GitHubSourceConfig, CodeChunk

logger = structlog.get_logger()

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".md": "markdown",
}


class GitHubIndexer:
    def __init__(self, org_id: str, config: GitHubSourceConfig):
        self.org_id = org_id
        self.config = config
        self.repos_dir = Path(settings.repos_dir) / org_id
        self.repos_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_matching_repos(self) -> list[dict]:
        repos = []
        headers = {"Authorization": f"token {settings.github_token}"}

        async with httpx.AsyncClient() as client:
            for pattern in self.config.include_patterns:
                if "/" in pattern:
                    owner, repo_pattern = pattern.split("/", 1)

                    if "*" not in repo_pattern:
                        response = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo_pattern}",
                            headers=headers,
                        )
                        if response.status_code == 200:
                            repos.append(response.json())
                    else:
                        page = 1
                        while True:
                            response = await client.get(
                                f"https://api.github.com/users/{owner}/repos",
                                headers=headers,
                                params={"page": page, "per_page": 100},
                            )
                            if response.status_code != 200:
                                break

                            page_repos = response.json()
                            if not page_repos:
                                break

                            for repo in page_repos:
                                if fnmatch(
                                    repo["name"], repo_pattern.replace("*", "*")
                                ):
                                    if not self._is_excluded(repo["full_name"]):
                                        repos.append(repo)
                            page += 1

                elif pattern.startswith("topic:"):
                    topic = pattern.replace("topic:", "")
                    response = await client.get(
                        "https://api.github.com/search/repositories",
                        headers=headers,
                        params={"q": f"topic:{topic}", "per_page": 100},
                    )
                    if response.status_code == 200:
                        for repo in response.json().get("items", []):
                            if not self._is_excluded(repo["full_name"]):
                                repos.append(repo)

        logger.info("github_repos_fetched", count=len(repos), org_id=self.org_id)
        return repos

    def _is_excluded(self, repo_full_name: str) -> bool:
        for pattern in self.config.exclude_patterns:
            if fnmatch(repo_full_name, pattern):
                return True
        return False

    async def clone_or_pull_repo(self, repo_url: str, repo_name: str) -> Path:
        repo_path = self.repos_dir / repo_name

        if repo_path.exists():
            logger.info("pulling_repo", repo=repo_name)
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
        else:
            logger.info("cloning_repo", repo=repo_name)
            clone_url = repo_url
            if settings.github_token:
                clone_url = repo_url.replace(
                    "https://github.com",
                    f"https://{settings.github_token}@github.com",
                )
            Repo.clone_from(clone_url, repo_path)

        return repo_path

    async def index_repo(self, repo_path: Path, repo_name: str) -> list[CodeChunk]:
        chunks = []

        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue

            rel_path = str(file_path.relative_to(repo_path))

            if not self._matches_file_patterns(rel_path):
                continue

            if self._matches_exclude_patterns(rel_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                language = self._detect_language(file_path)

                file_chunks = self._chunk_file(
                    content=content,
                    repo=repo_name,
                    file_path=rel_path,
                    language=language,
                )
                chunks.extend(file_chunks)
            except Exception as e:
                logger.warning("file_indexing_failed", file=rel_path, error=str(e))

        logger.info("repo_indexed", repo=repo_name, chunks=len(chunks))
        return chunks

    def _matches_file_patterns(self, file_path: str) -> bool:
        for pattern in self.config.file_patterns:
            if fnmatch(file_path, pattern):
                return True
        return False

    def _matches_exclude_patterns(self, file_path: str) -> bool:
        for pattern in self.config.exclude_file_patterns:
            if fnmatch(file_path, pattern):
                return True
        return False

    def _detect_language(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        return LANGUAGE_MAP.get(suffix, "unknown")

    def _chunk_file(
        self,
        content: str,
        repo: str,
        file_path: str,
        language: str,
    ) -> list[CodeChunk]:
        chunks = []
        lines = content.split("\n")
        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap

        current_chunk = []
        current_start = 1
        char_count = 0

        for i, line in enumerate(lines, 1):
            current_chunk.append(line)
            char_count += len(line) + 1

            if char_count >= chunk_size:
                chunk_content = "\n".join(current_chunk)
                chunk_id = self._generate_chunk_id(repo, file_path, current_start)

                chunks.append(
                    CodeChunk(
                        id=chunk_id,
                        content=chunk_content,
                        repo=repo,
                        file_path=file_path,
                        language=language,
                        chunk_type="other",
                        line_start=current_start,
                        line_end=i,
                    )
                )

                overlap_lines = int(overlap / (char_count / len(current_chunk)))
                current_chunk = (
                    current_chunk[-overlap_lines:] if overlap_lines > 0 else []
                )
                current_start = max(1, i - overlap_lines + 1)
                char_count = sum(len(line) + 1 for line in current_chunk)

        if current_chunk:
            chunk_content = "\n".join(current_chunk)
            chunk_id = self._generate_chunk_id(repo, file_path, current_start)

            chunks.append(
                CodeChunk(
                    id=chunk_id,
                    content=chunk_content,
                    repo=repo,
                    file_path=file_path,
                    language=language,
                    chunk_type="other",
                    line_start=current_start,
                    line_end=len(lines),
                )
            )

        return chunks

    def _generate_chunk_id(self, repo: str, file_path: str, line_start: int) -> str:
        content = f"{self.org_id}:{repo}:{file_path}:{line_start}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
