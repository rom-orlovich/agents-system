#!/usr/bin/env python3
"""
CLI instance heartbeat - updates last_heartbeat every 30 seconds.
Runs in background to keep instance marked as active.
"""

import asyncio
import os
import signal
import sys
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

logger = structlog.get_logger()

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global shutdown_flag
    logger.info("shutdown_signal_received", signal=signum)
    shutdown_flag = True


async def update_heartbeat():
    """Update heartbeat timestamp in database."""
    try:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            return

        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        hostname = os.environ.get("HOSTNAME", "unknown")

        async with async_session() as session:
            await session.execute(
                text("""
                    UPDATE cli_instances
                    SET last_heartbeat = :heartbeat
                    WHERE hostname = :hostname AND active = true
                """),
                {
                    "heartbeat": datetime.utcnow(),
                    "hostname": hostname
                }
            )
            await session.commit()

        logger.debug("heartbeat_updated", hostname=hostname)

    except Exception as e:
        logger.warning("heartbeat_failed", error=str(e))


async def mark_inactive():
    """Mark this instance as inactive in database."""
    try:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            return

        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        hostname = os.environ.get("HOSTNAME", "unknown")

        async with async_session() as session:
            await session.execute(
                text("""
                    UPDATE cli_instances
                    SET active = false, last_heartbeat = :heartbeat
                    WHERE hostname = :hostname
                """),
                {
                    "heartbeat": datetime.utcnow(),
                    "hostname": hostname
                }
            )
            await session.commit()

        logger.info("instance_marked_inactive", hostname=hostname)

    except Exception as e:
        logger.warning("failed_to_mark_inactive", error=str(e))


async def main():
    """Main heartbeat loop."""
    global shutdown_flag

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("heartbeat_started", interval=30)

    try:
        while not shutdown_flag:
            await update_heartbeat()
            await asyncio.sleep(30)  # Update every 30 seconds

    except Exception as e:
        logger.error("heartbeat_error", error=str(e))

    finally:
        # Mark as inactive on shutdown
        logger.info("heartbeat_stopping")
        await mark_inactive()
        logger.info("heartbeat_stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("heartbeat_interrupted")
        sys.exit(0)
