#!/usr/bin/env python3
"""
Unified CLI testing script for Claude and Cursor.
Tests CLI access and logs results to database.
Uses CLI runners from cli folder.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.factory import get_cli_runner
from cli.base import CLIResult

logger = structlog.get_logger()


async def test_claude_version() -> tuple[bool, str]:
    """Test Claude CLI version using CLI runner."""
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
            version = stdout.decode().strip()
            logger.info("claude_version_check_passed", output=version)
            return True, version
        else:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            logger.warning(
                "claude_version_check_failed",
                returncode=process.returncode,
                error=error_msg
            )
            return False, error_msg

    except asyncio.TimeoutError:
        logger.error("claude_version_check_timeout")
        return False, "Timeout"
    except FileNotFoundError:
        logger.error("claude_not_found", message="Claude CLI not installed")
        return False, "CLI not found"
    except Exception as e:
        logger.error("claude_check_error", error=str(e))
        return False, str(e)


async def test_cursor_version() -> tuple[bool, str]:
    """Test Cursor CLI version."""
    try:
        process = await asyncio.create_subprocess_exec(
            "runuser",
            "-l",
            "agent",
            "-c",
            "agent --version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=30.0
        )

        if process.returncode == 0:
            version = stdout.decode().strip()
            logger.info("cursor_version_check_passed", output=version)
            return True, version
        else:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            logger.warning(
                "cursor_version_check_failed",
                returncode=process.returncode,
                error=error_msg
            )
            return False, error_msg

    except asyncio.TimeoutError:
        logger.error("cursor_version_check_timeout")
        return False, "Timeout"
    except FileNotFoundError:
        logger.error("cursor_not_found", message="Cursor CLI not installed")
        return False, "CLI not found"
    except Exception as e:
        logger.error("cursor_check_error", error=str(e))
        return False, str(e)


async def test_claude_prompt() -> tuple[bool, str]:
    """Test Claude CLI with a simple prompt using CLI runner."""
    try:
        runner = get_cli_runner()
        output_queue: asyncio.Queue[str | None] = asyncio.Queue()
        test_dir = Path("/tmp")
        test_dir.mkdir(exist_ok=True)

        result: CLIResult = await runner.run(
            prompt="Say 'CLI test successful' and nothing else",
            working_dir=test_dir,
            output_queue=output_queue,
            task_id="test-cli",
            timeout_seconds=60,
        )

        if result.success:
            logger.info("claude_prompt_test_passed", output=result.output[:200])
            return True, "Prompt test passed"
        else:
            error_msg = result.error or "Unknown error"
            logger.warning("claude_prompt_test_failed", error=error_msg[:500])
            return False, error_msg[:500]

    except asyncio.TimeoutError:
        logger.error("claude_prompt_test_timeout")
        return False, "Timeout"
    except Exception as e:
        logger.error("claude_prompt_test_error", error=str(e))
        return False, str(e)


async def test_cursor_prompt() -> tuple[bool, str]:
    """Test Cursor CLI with a simple prompt using CLI runner."""
    try:
        runner = get_cli_runner()
        output_queue: asyncio.Queue[str | None] = asyncio.Queue()
        test_dir = Path("/tmp")
        test_dir.mkdir(exist_ok=True)

        result: CLIResult = await runner.run(
            prompt="Say CLI test successful and nothing else",
            working_dir=test_dir,
            output_queue=output_queue,
            task_id="test-cli",
            timeout_seconds=60,
        )

        if result.success:
            logger.info("cursor_prompt_test_passed", output=result.output[:200])
            return True, "Prompt test passed"
        else:
            error_msg = result.error or "Unknown error"
            logger.warning("cursor_prompt_test_failed", error=error_msg[:500])
            return False, error_msg[:500]

    except asyncio.TimeoutError:
        logger.error("cursor_prompt_test_timeout")
        return False, "Timeout"
    except Exception as e:
        logger.error("cursor_prompt_test_error", error=str(e))
        return False, str(e)


async def check_claude_credentials() -> bool:
    """Check if Claude credentials exist."""
    creds_paths = [
        Path.home() / ".claude" / ".credentials.json",
        Path("/home/agent/.claude/.credentials.json"),
        Path("/root/.claude/.credentials.json"),
        Path("/data/credentials/.credentials.json"),
        Path("/app/.claude/.credentials.json"),
    ]

    for path in creds_paths:
        try:
            if path.exists():
                logger.info("claude_credentials_found", path=str(path))
                return True
        except PermissionError:
            continue

    if os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("claude_api_key_found_in_env")
        return True

    logger.warning("no_claude_credentials_found", checked_paths=[str(p) for p in creds_paths])
    return False


async def check_cursor_credentials() -> bool:
    """Check if Cursor credentials exist."""
    if os.environ.get("CURSOR_API_KEY"):
        logger.info("cursor_api_key_found_in_env")
        return True

    cursor_config_paths = [
        Path.home() / ".cursor" / "cli-config.json",
        Path("/home/agent/.cursor/cli-config.json"),
    ]

    for path in cursor_config_paths:
        if path.exists():
            logger.info("cursor_config_found", path=str(path))
            return True

    logger.warning("no_cursor_credentials_found")
    return False


async def log_test_results_to_db(
    provider: str,
    version: str,
    version_test_passed: bool,
    prompt_test_passed: bool,
    test_details: str
) -> None:
    """Log CLI test results to database (non-blocking)."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import text

        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            return

        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS cli_test_results (
                    id SERIAL PRIMARY KEY,
                    provider VARCHAR(50) NOT NULL,
                    version VARCHAR(100),
                    version_test_passed BOOLEAN NOT NULL,
                    prompt_test_passed BOOLEAN NOT NULL,
                    overall_status VARCHAR(50) NOT NULL,
                    test_details TEXT,
                    hostname VARCHAR(255),
                    tested_at TIMESTAMP DEFAULT NOW()
                )
            """))

            hostname = os.environ.get("HOSTNAME", "unknown")
            overall_status = "passed" if (version_test_passed and prompt_test_passed) else "failed"

            await session.execute(
                text("""
                    INSERT INTO cli_test_results 
                    (provider, version, version_test_passed, prompt_test_passed, overall_status, test_details, hostname, tested_at)
                    VALUES (:provider, :version, :version_passed, :prompt_passed, :status, :details, :hostname, :tested_at)
                """),
                {
                    "provider": provider,
                    "version": version,
                    "version_passed": version_test_passed,
                    "prompt_passed": prompt_test_passed,
                    "status": overall_status,
                    "details": test_details,
                    "hostname": hostname,
                    "tested_at": datetime.utcnow()
                }
            )

            await session.commit()

        logger.info(
            "cli_test_results_logged",
            provider=provider,
            version=version,
            overall_status=overall_status
        )

    except Exception as e:
        logger.warning("failed_to_log_test_results", error=str(e))


async def main() -> int:
    """Run CLI tests based on provider."""
    provider = os.environ.get("CLI_PROVIDER", "claude").lower()
    os.environ["CLI_PROVIDER"] = provider
    logger.info("starting_cli_tests", provider=provider)

    if provider == "claude":
        has_creds = await check_claude_credentials()
        if not has_creds:
            logger.warning("skipping_cli_tests_no_credentials", provider=provider)
            try:
                await log_test_results_to_db(
                    provider=provider,
                    version="unknown",
                    version_test_passed=False,
                    prompt_test_passed=False,
                    test_details="No credentials found"
                )
            except Exception:
                pass
            return 0

        version_ok, version = await test_claude_version()
        if not version_ok:
            logger.error("cli_version_test_failed", provider=provider, error=version)
            try:
                await log_test_results_to_db(
                    provider=provider,
                    version=version,
                    version_test_passed=False,
                    prompt_test_passed=False,
                    test_details=f"Version check failed: {version}"
                )
            except Exception:
                pass
            return 1

        prompt_ok, prompt_details = await test_claude_prompt()
        if not prompt_ok:
            logger.warning("cli_prompt_test_failed_non_fatal", provider=provider)

        test_details = f"Version: {version}, Prompt: {prompt_details}"

        try:
            await log_test_results_to_db(
                provider=provider,
                version=version,
                version_test_passed=version_ok,
                prompt_test_passed=prompt_ok,
                test_details=test_details
            )
        except Exception:
            pass

        if version_ok and prompt_ok:
            logger.info("cli_tests_completed_successfully", provider=provider, version=version)
            return 0
        else:
            logger.warning("cli_tests_completed_with_warnings", provider=provider, version_ok=version_ok, prompt_ok=prompt_ok)
            return 1 if not version_ok else 0

    elif provider == "cursor":
        has_creds = await check_cursor_credentials()
        if not has_creds:
            logger.warning("skipping_cli_tests_no_credentials", provider=provider)
            try:
                await log_test_results_to_db(
                    provider=provider,
                    version="unknown",
                    version_test_passed=False,
                    prompt_test_passed=False,
                    test_details="No credentials found"
                )
            except Exception:
                pass
            return 0

        version_ok, version = await test_cursor_version()
        if not version_ok:
            logger.error("cli_version_test_failed", provider=provider, error=version)
            try:
                await log_test_results_to_db(
                    provider=provider,
                    version=version,
                    version_test_passed=False,
                    prompt_test_passed=False,
                    test_details=f"Version check failed: {version}"
                )
            except Exception:
                pass
            return 1

        prompt_ok, prompt_details = await test_cursor_prompt()
        if not prompt_ok:
            logger.warning("cli_prompt_test_failed_non_fatal", provider=provider)

        test_details = f"Version: {version}, Prompt: {prompt_details}"

        try:
            await log_test_results_to_db(
                provider=provider,
                version=version,
                version_test_passed=version_ok,
                prompt_test_passed=prompt_ok,
                test_details=test_details
            )
        except Exception:
            pass

        if version_ok and prompt_ok:
            logger.info("cli_tests_completed_successfully", provider=provider, version=version)
            return 0
        else:
            logger.warning("cli_tests_completed_with_warnings", provider=provider, version_ok=version_ok, prompt_ok=prompt_ok)
            return 1 if not version_ok else 0

    else:
        logger.error("unknown_provider", provider=provider)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
