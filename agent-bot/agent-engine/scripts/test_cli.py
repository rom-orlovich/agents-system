#!/usr/bin/env python3
"""Simple CLI test script."""

import asyncio
import os
import sys
from pathlib import Path

import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.factory import get_cli_runner
from cli.base import CLIResult

logger = structlog.get_logger()


async def test_version(provider: str) -> tuple[bool, str]:
    """Test CLI version."""
    cmd = "claude" if provider == "claude" else "agent"
    try:
        process = await asyncio.create_subprocess_exec(
            cmd,
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)

        if process.returncode == 0:
            version = stdout.decode().strip()
            logger.info(f"{provider}_version_check_passed", output=version)
            return True, version
        else:
            error = stderr.decode().strip() or stdout.decode().strip()
            logger.warning(f"{provider}_version_check_failed", error=error)
            return False, error
    except Exception as e:
        logger.error(f"{provider}_version_error", error=str(e))
        return False, str(e)


async def test_prompt(provider: str) -> tuple[bool, str]:
    """Test CLI with simple prompt."""
    try:
        runner = get_cli_runner()
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        result: CLIResult = await runner.run(
            prompt="Say 'CLI test successful' and nothing else",
            working_dir=Path("/tmp"),
            output_queue=queue,
            task_id="test-cli",
            timeout_seconds=60,
        )

        if result.success:
            logger.info(f"{provider}_prompt_test_passed", output=result.output[:200])
            return True, "Prompt test passed"
        else:
            logger.warning(f"{provider}_prompt_test_failed", error=result.error)
            return False, result.error or "Unknown error"
    except Exception as e:
        logger.error(f"{provider}_prompt_error", error=str(e))
        return False, str(e)


async def check_credentials(provider: str) -> bool:
    """Check if credentials exist."""
    if provider == "claude":
        creds = Path.home() / ".claude" / ".credentials.json"
        if creds.exists():
            logger.info("claude_credentials_found", path=str(creds))
            return True
        if os.environ.get("ANTHROPIC_API_KEY"):
            logger.info("claude_api_key_found")
            return True
    elif provider == "cursor":
        if os.environ.get("CURSOR_API_KEY"):
            logger.info("cursor_api_key_found")
            return True

    logger.warning(f"no_{provider}_credentials_found")
    return False


async def main() -> int:
    provider = os.environ.get("CLI_PROVIDER", "claude").lower()
    logger.info("starting_cli_tests", provider=provider)

    if not await check_credentials(provider):
        logger.warning("skipping_tests_no_credentials")
        return 0

    version_ok, version = await test_version(provider)
    if not version_ok:
        logger.error("version_test_failed", error=version)
        return 1

    prompt_ok, details = await test_prompt(provider)

    if version_ok and prompt_ok:
        logger.info("cli_tests_passed", provider=provider, version=version)
        return 0
    else:
        logger.warning(
            "cli_tests_completed_with_warnings",
            version_ok=version_ok,
            prompt_ok=prompt_ok,
        )
        return 0 if version_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
