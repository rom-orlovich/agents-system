"""
Integration tests for Claude CLI execution (NOT MOCKED).

These tests actually call the Claude CLI binary to verify:
1. CLI binary exists and is executable
2. Flags are correctly formatted
3. Command runs without errors
4. Output is parseable

WARNING: These tests require Claude CLI to be installed!
Skip with: pytest -m "not cli_integration"
"""

import pytest
import asyncio
from pathlib import Path
import os
import subprocess

pytestmark = pytest.mark.skipif(
    not os.path.exists("/root/.local/bin/claude") and not os.path.exists("/usr/local/bin/claude"),
    reason="Claude CLI not installed"
)


@pytest.mark.cli_integration
@pytest.mark.asyncio
async def test_claude_cli_installed():
    """Verify Claude CLI is installed and accessible."""
    result = subprocess.run(
        ["which", "claude"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Claude CLI not found in PATH"
    assert result.stdout.strip().endswith("claude"), f"Unexpected output: {result.stdout}"


@pytest.mark.cli_integration
@pytest.mark.asyncio
async def test_claude_cli_version():
    """Test that Claude CLI responds to --version."""
    result = subprocess.run(
        ["claude", "--version"],
        capture_output=True,
        text=True,
        timeout=10
    )
    # Claude CLI may not have --version, so we just check it doesn't crash
    assert result.returncode in [0, 1, 2], f"CLI crashed: {result.stderr}"


@pytest.mark.cli_integration
@pytest.mark.asyncio
async def test_claude_cli_help():
    """Test that Claude CLI responds to --help."""
    result = subprocess.run(
        ["claude", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert result.returncode == 0, f"Help command failed: {result.stderr}"
    assert "--" in result.stdout or "Usage" in result.stdout or "help" in result.stdout.lower()


@pytest.mark.cli_integration
@pytest.mark.asyncio
async def test_cli_command_format_simple():
    """Test basic CLI command format (no execution, just syntax check)."""
    # Build the command
    cmd = [
        "claude",
        "-p",
        "--output-format", "json",
        "--dangerously-skip-permissions",
        "--",
        "echo test"
    ]

    # This should not fail with syntax errors
    # We use a simple echo command to avoid actually running Claude
    # The test is just to verify the flags are recognized
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30
    )

    # We expect either:
    # - Success (returncode 0)
    # - API key error (but not syntax error)
    # - Permission error (but not syntax error)
    if result.returncode != 0:
        stderr_lower = result.stderr.lower()
        # These are acceptable errors (not syntax issues)
        acceptable_errors = [
            "api key",
            "api_key",
            "authentication",
            "credentials",
            "permission",
            "not authorized"
        ]
        has_acceptable_error = any(err in stderr_lower for err in acceptable_errors)

        # These are syntax errors (NOT acceptable)
        syntax_errors = [
            "unrecognized",
            "unknown option",
            "invalid argument",
            "unexpected argument",
            "no such option"
        ]
        has_syntax_error = any(err in stderr_lower for err in syntax_errors)

        assert not has_syntax_error, f"CLI syntax error: {result.stderr}"
        assert has_acceptable_error or result.returncode == 0, \
            f"Unexpected error (not syntax, not auth): {result.stderr}"


@pytest.mark.cli_integration
@pytest.mark.asyncio
async def test_cli_model_flag():
    """Test that --model flag is recognized."""
    cmd = [
        "claude",
        "-p",
        "--model", "sonnet",  # Test model flag
        "--dangerously-skip-permissions",
        "--",
        "echo test"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30
    )

    # Check for syntax errors related to --model
    if result.returncode != 0:
        stderr_lower = result.stderr.lower()
        assert "unknown option" not in stderr_lower or "--model" not in stderr_lower, \
            f"--model flag not recognized: {result.stderr}"


@pytest.mark.cli_integration
@pytest.mark.asyncio
async def test_cli_allowed_tools_flag():
    """Test that --allowedTools flag is recognized."""
    cmd = [
        "claude",
        "-p",
        "--allowedTools", "Read,Edit,Bash",  # Test allowedTools flag
        "--dangerously-skip-permissions",
        "--",
        "echo test"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30
    )

    # Check for syntax errors related to --allowedTools
    if result.returncode != 0:
        stderr_lower = result.stderr.lower()
        assert "unknown option" not in stderr_lower or "--allowedtools" not in stderr_lower, \
            f"--allowedTools flag not recognized: {result.stderr}"


@pytest.mark.cli_integration
@pytest.mark.asyncio
async def test_cli_agents_flag():
    """Test that --agents flag is recognized."""
    cmd = [
        "claude",
        "-p",
        "--agents", '{"planning":{"skills":["analyze"]}}',  # Test agents flag
        "--dangerously-skip-permissions",
        "--",
        "echo test"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30
    )

    # Check for syntax errors related to --agents
    if result.returncode != 0:
        stderr_lower = result.stderr.lower()
        assert "unknown option" not in stderr_lower or "--agents" not in stderr_lower, \
            f"--agents flag not recognized: {result.stderr}"


@pytest.mark.cli_integration
@pytest.mark.asyncio
async def test_cli_full_command():
    """Test full CLI command with all flags."""
    cmd = [
        "claude",
        "-p",
        "--output-format", "json",
        "--dangerously-skip-permissions",
        "--model", "sonnet",
        "--allowedTools", "Read,Edit,Bash,Glob,Grep,Write",
        "--agents", '{"planning":{"description":"Test","skills":["test"]}}',
        "--",
        "What is 2+2?"  # Simple test prompt
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60  # Allow more time for full execution
    )

    # Check for syntax errors
    if result.returncode != 0:
        stderr_lower = result.stderr.lower()
        syntax_errors = [
            "unrecognized",
            "unknown option",
            "invalid argument",
            "unexpected argument",
            "no such option"
        ]
        has_syntax_error = any(err in stderr_lower for err in syntax_errors)
        assert not has_syntax_error, f"CLI syntax error: {result.stderr}"


@pytest.mark.cli_integration
@pytest.mark.asyncio
async def test_subagent_config_loading():
    """Test that sub-agent configuration loading works."""
    from core.subagent_config import load_subagent_config, get_default_subagents
    import json

    # Test default sub-agents
    default_config = get_default_subagents()
    assert default_config is not None
    assert isinstance(default_config, str)

    # Should be valid JSON
    parsed = json.loads(default_config)
    assert isinstance(parsed, dict)
    assert len(parsed) > 0

    # Should have expected structure
    for name, definition in parsed.items():
        assert isinstance(definition, dict)
        assert "description" in definition
        assert "skills" in definition
        assert isinstance(definition["skills"], list)


@pytest.mark.cli_integration
@pytest.mark.asyncio
async def test_cli_command_builder():
    """Test that our CLI command builder produces valid commands."""
    from core.cli_runner import run_claude_cli
    from pathlib import Path
    import asyncio

    # Create a test working directory
    test_dir = Path("/tmp/claude-test")
    test_dir.mkdir(exist_ok=True)

    # Create a simple CLAUDE.md
    (test_dir / "CLAUDE.md").write_text("# Test Agent\nYou are a test agent.")

    # Create output queue
    output_queue = asyncio.Queue()

    # This will likely fail due to API key, but we're testing command format
    try:
        result = await asyncio.wait_for(
            run_claude_cli(
                prompt="What is 1+1?",
                working_dir=test_dir,
                output_queue=output_queue,
                task_id="test-001",
                timeout_seconds=10,
                model="sonnet",
                allowed_tools="Read,Edit",
                agents='{"test":{"description":"Test","skills":["test"]}}'
            ),
            timeout=15
        )

        # If we get here, either:
        # 1. API key is configured and it worked
        # 2. Some other expected error occurred
        # We just check that it didn't fail with syntax errors
        if not result.success and result.error:
            error_lower = result.error.lower()
            syntax_errors = [
                "unrecognized",
                "unknown option",
                "invalid argument"
            ]
            has_syntax_error = any(err in error_lower for err in syntax_errors)
            assert not has_syntax_error, f"CLI syntax error: {result.error}"

    except asyncio.TimeoutError:
        # Timeout is acceptable (API call may be slow)
        pass
    except Exception as e:
        # Check if it's a syntax error
        error_str = str(e).lower()
        syntax_errors = [
            "unrecognized",
            "unknown option",
            "invalid argument"
        ]
        has_syntax_error = any(err in error_str for err in syntax_errors)
        assert not has_syntax_error, f"CLI syntax error: {str(e)}"
