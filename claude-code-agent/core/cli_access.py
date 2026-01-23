"""CLI access testing utilities."""

import subprocess
import structlog

logger = structlog.get_logger()


async def test_cli_access() -> bool:
    """
    Run simple test with Claude CLI. Returns True if successful.
    
    Returns:
        bool: True if CLI test succeeds, False otherwise
    """
    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "json", "--dangerously-skip-permissions", "--", "test"],
            capture_output=True,
            timeout=10,
            text=True
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.warning("CLI access test failed", error=str(e))
        return False
