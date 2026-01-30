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

        blocked_dirs = {"secrets", ".credentials", ".ssh"}
        for part in path.parts:
            if part in blocked_dirs:
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
