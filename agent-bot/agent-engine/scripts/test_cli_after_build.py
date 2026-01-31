#!/usr/bin/env python3
"""
Test CLI after Docker build and update status.
This script runs inside the container after build to verify CLI is working.
Adapted for agent-bot microservices architecture.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

import structlog

logger = structlog.get_logger()


async def test_cli_access() -> bool:
    """Test if CLI is accessible and working."""
    try:
        process = await asyncio.create_subprocess_exec(
            "claude",
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=30.0
        )

        if process.returncode == 0:
            logger.info("cli_version_check_passed", output=stdout.decode().strip())
            return True
        else:
            logger.warning(
                "cli_version_check_failed",
                returncode=process.returncode,
                stderr=stderr.decode()
            )
            return False

    except asyncio.TimeoutError:
        logger.error("cli_version_check_timeout")
        return False
    except FileNotFoundError:
        logger.error("cli_not_found", message="Claude CLI not installed")
        return False
    except Exception as e:
        logger.error("cli_check_error", error=str(e))
        return False


async def test_cli_prompt() -> bool:
    """Test if CLI can process a simple prompt."""
    try:
        process = await asyncio.create_subprocess_exec(
            "claude",
            "-p",
            "Say 'CLI test successful' and nothing else",
            "--output-format", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=60.0
        )

        if process.returncode == 0:
            logger.info("cli_prompt_test_passed")
            return True
        else:
            logger.warning(
                "cli_prompt_test_failed",
                returncode=process.returncode,
                stderr=stderr.decode()[:500]
            )
            return False

    except asyncio.TimeoutError:
        logger.error("cli_prompt_test_timeout")
        return False
    except Exception as e:
        logger.error("cli_prompt_test_error", error=str(e))
        return False


async def check_credentials() -> bool:
    """Check if credentials file exists."""
    creds_paths = [
        Path.home() / ".claude" / ".credentials.json",
        Path("/home/agent/.claude/.credentials.json"),
        Path("/root/.claude/.credentials.json"),
        Path("/data/credentials/.credentials.json"),
        Path("/app/.claude/.credentials.json"),
    ]

    for path in creds_paths:
        if path.exists():
            logger.info("credentials_found", path=str(path))
            return True

    # Check for API key
    if os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("api_key_found_in_env")
        return True

    logger.warning("no_credentials_found", checked_paths=[str(p) for p in creds_paths])
    return False


async def main() -> int:
    """Run all CLI tests."""
    logger.info("starting_cli_tests")

    # Check credentials
    has_creds = await check_credentials()
    if not has_creds:
        logger.warning("skipping_cli_tests_no_credentials")
        return 0  # Not an error, just skip

    # Test CLI version
    version_ok = await test_cli_access()
    if not version_ok:
        logger.error("cli_version_test_failed")
        return 1

    # Test CLI prompt (optional, may fail if rate limited)
    prompt_ok = await test_cli_prompt()
    if not prompt_ok:
        logger.warning("cli_prompt_test_failed_non_fatal")
        # Don't fail build for prompt test failure

    logger.info("cli_tests_completed", version_ok=version_ok, prompt_ok=prompt_ok)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
