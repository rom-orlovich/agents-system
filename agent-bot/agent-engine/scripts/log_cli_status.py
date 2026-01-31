#!/usr/bin/env python3
"""
Log CLI status to database for monitoring.
Runs at container startup to track CLI health.
"""

import asyncio
import os
import sys
from datetime import datetime

import structlog

logger = structlog.get_logger()


async def get_cli_version(provider: str) -> tuple[bool, str]:
    """Get CLI version for the specified provider."""
    try:
        if provider == "claude":
            cmd = ["claude", "--version"]
        elif provider == "cursor":
            # Need to run as agent user with proper PATH
            cmd = ["runuser", "-l", "agent", "-c", "agent --version"]
        else:
            return False, f"Unknown provider: {provider}"

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)

        if process.returncode == 0:
            version = stdout.decode().strip()
            return True, version
        else:
            return False, stderr.decode().strip()

    except asyncio.TimeoutError:
        return False, "Timeout"
    except FileNotFoundError:
        return False, "CLI not found"
    except Exception as e:
        return False, str(e)


async def log_status_to_db(provider: str, version: str, status: str):
    """Log CLI status to database and mark instance as active."""
    try:
        # Import here to avoid circular dependencies
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import text

        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.warning("no_database_url", message="Skipping DB logging")
            return

        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            # Create health log table if not exists
            await session.execute(
                text("""
                CREATE TABLE IF NOT EXISTS cli_health (
                    id SERIAL PRIMARY KEY,
                    provider VARCHAR(50) NOT NULL,
                    version VARCHAR(100),
                    status VARCHAR(50) NOT NULL,
                    hostname VARCHAR(255),
                    checked_at TIMESTAMP DEFAULT NOW()
                )
            """)
            )

            # Create active instances table if not exists
            await session.execute(
                text("""
                CREATE TABLE IF NOT EXISTS cli_instances (
                    id SERIAL PRIMARY KEY,
                    provider VARCHAR(50) NOT NULL,
                    version VARCHAR(100),
                    hostname VARCHAR(255) UNIQUE NOT NULL,
                    container_id VARCHAR(255),
                    active BOOLEAN DEFAULT true,
                    started_at TIMESTAMP DEFAULT NOW(),
                    last_heartbeat TIMESTAMP DEFAULT NOW(),
                    UNIQUE(hostname)
                )
            """)
            )

            hostname = os.environ.get("HOSTNAME", "unknown")
            container_id = hostname  # Docker sets HOSTNAME to container ID

            # Insert health check log
            await session.execute(
                text("""
                    INSERT INTO cli_health (provider, version, status, hostname, checked_at)
                    VALUES (:provider, :version, :status, :hostname, :checked_at)
                """),
                {
                    "provider": provider,
                    "version": version,
                    "status": status,
                    "hostname": hostname,
                    "checked_at": datetime.utcnow(),
                },
            )

            # Insert or update active instance
            await session.execute(
                text("""
                    INSERT INTO cli_instances (provider, version, hostname, container_id, active, started_at, last_heartbeat)
                    VALUES (:provider, :version, :hostname, :container_id, true, NOW(), NOW())
                    ON CONFLICT (hostname)
                    DO UPDATE SET
                        provider = EXCLUDED.provider,
                        version = EXCLUDED.version,
                        active = true,
                        started_at = NOW(),
                        last_heartbeat = NOW()
                """),
                {
                    "provider": provider,
                    "version": version,
                    "hostname": hostname,
                    "container_id": container_id,
                },
            )

            await session.commit()

        logger.info(
            "cli_instance_activated",
            provider=provider,
            version=version,
            status=status,
            hostname=hostname,
            active=True,
        )

    except Exception as e:
        logger.warning("failed_to_log_status", error=str(e))


async def main():
    """Main entry point."""
    provider = os.environ.get("CLI_PROVIDER", "claude")

    logger.info("checking_cli_status", provider=provider)

    # Get CLI version
    success, version = await get_cli_version(provider)
    status = "healthy" if success else "unhealthy"

    # Log to database
    await log_status_to_db(provider, version, status)

    if success:
        logger.info("cli_healthy", provider=provider, version=version)
    else:
        logger.error("cli_unhealthy", provider=provider, error=version)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
