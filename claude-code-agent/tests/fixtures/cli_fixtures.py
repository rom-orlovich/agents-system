"""
CLI Testing Fixtures
====================

Provides fixtures for testing Claude CLI integration without expensive API calls.

Test Modes:
-----------
1. **Fake CLI Mode** (default)
   - Uses fake_claude_cli.sh script
   - No API calls, instant responses
   - Controlled via FAKE_CLAUDE_MODE env var

2. **Dry Run Mode**
   - Validates command syntax only
   - No process execution
   - Useful for command builder tests

3. **Real CLI Mode** (optional)
   - Uses actual Claude CLI binary
   - Makes real API calls (expensive!)
   - Only enabled via CLAUDE_TEST_REAL_CLI=1

Usage:
------
```python
# In your test
def test_something(fake_claude_cli):
    # fake_claude_cli fixture provides path to fake CLI
    result = subprocess.run([fake_claude_cli, "-p", "--", "test"], ...)

# Control response mode
def test_error(fake_claude_cli, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "auth_error")
    result = subprocess.run([fake_claude_cli, "-p", "--", "test"], ...)
```
"""

import os
import pytest
import subprocess
from pathlib import Path
from typing import Generator


# Test mode configuration
REAL_CLI_ENABLED = os.getenv("CLAUDE_TEST_REAL_CLI", "0") == "1"
FAKE_CLI_PATH = Path(__file__).parent / "fake_claude_cli.sh"


@pytest.fixture
def fake_claude_cli() -> str:
    """
    Provides path to fake Claude CLI for testing.

    Returns:
        str: Path to fake_claude_cli.sh

    Environment Variables:
        FAKE_CLAUDE_MODE: Response mode (success, error, timeout, etc.)
    """
    assert FAKE_CLI_PATH.exists(), f"Fake CLI not found: {FAKE_CLI_PATH}"
    assert os.access(FAKE_CLI_PATH, os.X_OK), f"Fake CLI not executable: {FAKE_CLI_PATH}"
    return str(FAKE_CLI_PATH)


@pytest.fixture
def fake_cli_success(fake_claude_cli, monkeypatch) -> str:
    """
    Fake CLI that returns successful response.

    Returns:
        str: Path to fake CLI (configured for success)
    """
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "success")
    return fake_claude_cli


@pytest.fixture
def fake_cli_error(fake_claude_cli, monkeypatch) -> str:
    """
    Fake CLI that returns error.

    Returns:
        str: Path to fake CLI (configured for error)
    """
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "error")
    return fake_claude_cli


@pytest.fixture
def fake_cli_timeout(fake_claude_cli, monkeypatch) -> str:
    """
    Fake CLI that hangs indefinitely (for timeout tests).

    Returns:
        str: Path to fake CLI (configured for timeout)
    """
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "timeout")
    return fake_claude_cli


@pytest.fixture
def fake_cli_auth_error(fake_claude_cli, monkeypatch) -> str:
    """
    Fake CLI that returns authentication error.

    Returns:
        str: Path to fake CLI (configured for auth error)
    """
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "auth_error")
    return fake_claude_cli


@pytest.fixture
def fake_cli_malformed(fake_claude_cli, monkeypatch) -> str:
    """
    Fake CLI that returns malformed JSON.

    Returns:
        str: Path to fake CLI (configured for malformed output)
    """
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "malformed")
    return fake_claude_cli


@pytest.fixture
def fake_cli_streaming(fake_claude_cli, monkeypatch) -> str:
    """
    Fake CLI that simulates streaming output.

    Returns:
        str: Path to fake CLI (configured for streaming)
    """
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "streaming")
    return fake_claude_cli


@pytest.fixture
def real_claude_cli() -> Generator[str, None, None]:
    """
    Provides path to real Claude CLI (if enabled).

    Only available when CLAUDE_TEST_REAL_CLI=1 is set.
    Skips test if real CLI is not available.

    Yields:
        str: Path to real claude binary

    Raises:
        pytest.skip: If real CLI testing is disabled or CLI not found
    """
    if not REAL_CLI_ENABLED:
        pytest.skip("Real CLI testing disabled (set CLAUDE_TEST_REAL_CLI=1 to enable)")

    # Find Claude CLI in PATH
    result = subprocess.run(
        ["which", "claude"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        pytest.skip("Claude CLI not found in PATH")

    cli_path = result.stdout.strip()
    yield cli_path


@pytest.fixture
def cli_test_workspace(tmp_path) -> Path:
    """
    Provides a temporary workspace for CLI tests.

    Creates:
    - Working directory
    - Sample CLAUDE.md
    - Sample files for Read tool

    Returns:
        Path: Temporary workspace directory
    """
    workspace = tmp_path / "cli_workspace"
    workspace.mkdir()

    # Create sample CLAUDE.md
    (workspace / "CLAUDE.md").write_text("""# Test Agent

You are a test agent for integration testing.

## Capabilities
- Analyze prompts
- Generate responses
- Use tools as needed

## Guidelines
- Keep responses concise
- Always respond in JSON format when possible
""")

    # Create sample files
    (workspace / "test_file.txt").write_text("Sample content for testing")
    (workspace / "README.md").write_text("# Test Project\n\nThis is a test.")

    return workspace


@pytest.fixture
def dry_run_mode(monkeypatch):
    """
    Enable dry-run mode (no actual process execution).

    When enabled, tests can validate command syntax without execution.

    Usage:
        def test_command_syntax(dry_run_mode):
            # Test command building logic only
            cmd = build_cli_command(...)
            assert "--model" in cmd
            assert "sonnet" in cmd
    """
    monkeypatch.setenv("DRY_RUN", "1")
    yield
    # Cleanup handled by monkeypatch


def is_dry_run() -> bool:
    """
    Check if dry-run mode is enabled.

    Returns:
        bool: True if DRY_RUN=1 is set
    """
    return os.getenv("DRY_RUN", "0") == "1"


def is_real_cli_enabled() -> bool:
    """
    Check if real CLI testing is enabled.

    Returns:
        bool: True if CLAUDE_TEST_REAL_CLI=1 is set
    """
    return REAL_CLI_ENABLED


# Pytest markers for conditional test execution
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "real_cli: Tests that require real Claude CLI (expensive, disabled by default)"
    )
    config.addinivalue_line(
        "markers",
        "fake_cli: Tests using fake Claude CLI (fast, no API calls)"
    )
    config.addinivalue_line(
        "markers",
        "dry_run: Tests that only validate command syntax (no execution)"
    )


def pytest_collection_modifyitems(config, items):
    """
    Automatically skip tests based on environment.

    - real_cli tests: Skip unless CLAUDE_TEST_REAL_CLI=1
    - fake_cli tests: Always run (default)
    - dry_run tests: Always run (default)
    """
    skip_real_cli = pytest.mark.skip(reason="Real CLI testing disabled (set CLAUDE_TEST_REAL_CLI=1)")

    for item in items:
        if "real_cli" in item.keywords and not is_real_cli_enabled():
            item.add_marker(skip_real_cli)
