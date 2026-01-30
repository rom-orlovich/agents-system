import structlog
from typing import Dict, Any


logger = structlog.get_logger()


class MCPClient:
    def __init__(self):
        self.servers = {
            "github": "github-mcp-server",
            "jira": "jira-mcp-server",
            "slack": "slack-mcp-server",
            "sentry": "sentry-mcp-server",
        }

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> bool:
        logger.info("mcp_tool_call", tool_name=name, arguments=arguments)

        try:
            server = self._get_server_for_tool(name)
            if not server:
                logger.error("unknown_mcp_tool", tool_name=name)
                return False

            result = await self._invoke_mcp_server(server, name, arguments)
            logger.info("mcp_tool_result", tool_name=name, success=True)
            return True

        except Exception as e:
            logger.error("mcp_tool_error", tool_name=name, error=str(e))
            return False

    def _get_server_for_tool(self, tool_name: str) -> str | None:
        if tool_name.startswith("github_"):
            return self.servers.get("github")
        elif tool_name.startswith("jira_"):
            return self.servers.get("jira")
        elif tool_name.startswith("slack_"):
            return self.servers.get("slack")
        elif tool_name.startswith("sentry_"):
            return self.servers.get("sentry")
        return None

    async def _invoke_mcp_server(
        self, server: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        logger.info(
            "invoking_mcp_server", server=server, tool=tool_name, args=arguments
        )
        return {"success": True}
