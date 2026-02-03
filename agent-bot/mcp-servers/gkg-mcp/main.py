import structlog

from config import settings
from gkg_mcp import mcp

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()


def main():
    logger.info("gkg_mcp_starting", port=settings.mcp_port)
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
