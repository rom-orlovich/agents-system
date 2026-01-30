import pytest
from pathlib import Path

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
